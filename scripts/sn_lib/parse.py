from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class Section:
    heading: str
    text: str

@dataclass
class Manuscript:
    title: str
    authors: list[str]
    abstract: str | None
    sections: list[Section]
    word_count: int
    reference_count: int
    source_path: str

    def to_dict(self) -> dict:
        return {**asdict(self), "sections": [asdict(s) for s in self.sections]}

HEADING_RE = re.compile(r"^(abstract|introduction|methods?|results?|discussion|conclusion|references|acknowledg(e)?ments?)\b", re.I)
REF_LINE_RE = re.compile(r"(?:^\[\d+\]|\(\d{4}\))")

def _split_headings(paragraphs: list[tuple[str, str]]) -> list[Section]:
    sections: list[Section] = []
    cur_head = "Body"
    buf: list[str] = []
    for style, text in paragraphs:
        is_h = style.startswith("Heading") or HEADING_RE.match(text.strip())
        if is_h and text.strip():
            if buf:
                sections.append(Section(cur_head, "\n".join(buf).strip()))
                buf = []
            cur_head = text.strip()
        else:
            if text.strip():
                buf.append(text)
    if buf:
        sections.append(Section(cur_head, "\n".join(buf).strip()))
    return sections

def _parse_docx(path: Path) -> Manuscript:
    from docx import Document
    doc = Document(str(path))
    paras = [(p.style.name if p.style else "", p.text) for p in doc.paragraphs]
    title = next((t for s, t in paras if s.startswith("Heading") or s == "Title"), paras[0][1] if paras else "")
    authors_line = ""
    for i, (_, t) in enumerate(paras):
        if t == title:
            if i + 1 < len(paras):
                authors_line = paras[i + 1][1]
            break
    authors = [a.strip() for a in re.split(r",| and ", authors_line) if a.strip()] if authors_line else []
    sections = _split_headings(paras)
    abstract = next((s.text for s in sections if s.heading.lower().startswith("abstract")), None)
    refs_section = next((s for s in sections if s.heading.lower().startswith("reference")), None)
    ref_count = len(re.findall(r"\[\d+\]|\(\d{4}\)", refs_section.text)) if refs_section else 0
    all_text = " ".join(s.text for s in sections)
    wc = len(all_text.split())
    return Manuscript(title.strip(), authors, abstract, sections, wc, ref_count, str(path))

def _parse_pdf(path: Path) -> Manuscript:
    import fitz
    doc = fitz.open(str(path))
    pages = [page.get_text("text") for page in doc]
    full = "\n".join(pages)
    if len(full.strip()) < 50:
        from .ocr import ocr_pdf
        full = ocr_pdf(path)
    lines = [l for l in full.splitlines() if l.strip()]
    title = lines[0] if lines else ""
    authors_line = lines[1] if len(lines) > 1 else ""
    authors = [a.strip() for a in re.split(r",| and ", authors_line) if a.strip() and len(a.strip()) < 60]
    blocks: list[tuple[str, str]] = []
    cur_head = "Body"
    cur_buf: list[str] = []
    for ln in lines:
        if HEADING_RE.match(ln.strip()):
            if cur_buf:
                blocks.append((cur_head, "\n".join(cur_buf)))
                cur_buf = []
            cur_head = ln.strip()
        else:
            cur_buf.append(ln)
    if cur_buf:
        blocks.append((cur_head, "\n".join(cur_buf)))
    sections = [Section(h, t) for h, t in blocks]
    abstract = next((s.text for s in sections if s.heading.lower().startswith("abstract")), None)
    refs_section = next((s for s in sections if s.heading.lower().startswith("reference")), None)
    ref_count = len(re.findall(r"\[\d+\]|\(\d{4}\)", refs_section.text)) if refs_section else 0
    wc = len(full.split())
    return Manuscript(title.strip(), authors, abstract, sections, wc, ref_count, str(path))

def parse_manuscript(path: str | Path) -> Manuscript:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".docx"}:
        return _parse_docx(p)
    if suffix == ".pdf":
        return _parse_pdf(p)
    raise ValueError(f"Unsupported extension: {suffix}")

def _main():
    import argparse, json, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    m = parse_manuscript(args.path)
    print(json.dumps(m.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
