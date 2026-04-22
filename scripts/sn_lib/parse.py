from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from .cli import emit_json

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

HEADING_NUMBER_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s*")
REF_LINE_RE = re.compile(r"(?m)^\s*(?:\[\d+\]|\d+\.)\s+")
REF_BRACKET_RE = re.compile(r"\[\d+\]")
KNOWN_HEADINGS = (
    "abstract",
    "introduction",
    "materials and methods",
    "materials & methods",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "acknowledgement",
    "acknowledgements",
    "acknowledgment",
    "acknowledgments",
)

def _is_heading_style(style: str) -> bool:
    return style.startswith("Heading")


def _normalized_heading(text: str) -> str:
    t = HEADING_NUMBER_RE.sub("", text.strip())
    return t.rstrip(":").strip().lower()


def _is_known_heading(text: str) -> bool:
    normalized = _normalized_heading(text)
    return normalized in KNOWN_HEADINGS


def _is_reference_heading(text: str) -> bool:
    return _normalized_heading(text).startswith("references")


def _is_abstract_heading(text: str) -> bool:
    return _normalized_heading(text).startswith("abstract")


def _count_references(text: str) -> int:
    bracketed = REF_BRACKET_RE.findall(text)
    if bracketed:
        return len(bracketed)
    numbered = REF_LINE_RE.findall(text)
    if numbered:
        return len(numbered)
    return len(re.findall(r"\b10\.\d{4,9}/\S+\b", text))

def _looks_like_title(style: str, text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if style == "Title":
        return True
    if _is_heading_style(style):
        return not _is_known_heading(t)
    return False

def _pick_docx_title(paragraphs: list[tuple[str, str]]) -> str:
    for style, text in paragraphs:
        if _looks_like_title(style, text):
            return text.strip()
    for style, text in paragraphs:
        t = text.strip()
        if not t:
            continue
        if _is_known_heading(t):
            continue
        if len(t.split()) >= 3:
            return t
    return paragraphs[0][1].strip() if paragraphs else ""

def _split_headings(paragraphs: list[tuple[str, str]]) -> list[Section]:
    sections: list[Section] = []
    cur_head = "Body"
    buf: list[str] = []
    for style, text in paragraphs:
        is_h = _is_heading_style(style) or _is_known_heading(text)
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
    title = _pick_docx_title(paras)
    authors_line = ""
    for i, (_, t) in enumerate(paras):
        if t == title:
            if i + 1 < len(paras):
                authors_line = paras[i + 1][1]
            break
    authors = [a.strip() for a in re.split(r",| and ", authors_line) if a.strip()] if authors_line else []
    sections = _split_headings(paras)
    abstract = next((s.text for s in sections if _is_abstract_heading(s.heading)), None)
    refs_section = next((s for s in sections if _is_reference_heading(s.heading)), None)
    ref_count = _count_references(refs_section.text) if refs_section else 0
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
        if _is_known_heading(ln):
            if cur_buf:
                blocks.append((cur_head, "\n".join(cur_buf)))
                cur_buf = []
            cur_head = ln.strip()
        else:
            cur_buf.append(ln)
    if cur_buf:
        blocks.append((cur_head, "\n".join(cur_buf)))
    sections = [Section(h, t) for h, t in blocks]
    abstract = next((s.text for s in sections if _is_abstract_heading(s.heading)), None)
    refs_section = next((s for s in sections if _is_reference_heading(s.heading)), None)
    ref_count = _count_references(refs_section.text) if refs_section else 0
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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--out", help="Optional path to write JSON output.")
    args = ap.parse_args()
    m = parse_manuscript(args.path)
    emit_json(m.to_dict(), args.out)

if __name__ == "__main__":
    _main()
