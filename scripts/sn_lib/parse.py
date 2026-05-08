from __future__ import annotations
import re
from dataclasses import dataclass, asdict, field
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
    references: list[str] = field(default_factory=list)
    article_type: str | None = None

    def to_dict(self) -> dict:
        return {**asdict(self), "sections": [asdict(s) for s in self.sections]}

    def to_summary_dict(self, max_heading_count: int = 12) -> dict:
        headings = [s.heading for s in self.sections if s.heading][:max_heading_count]
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "section_headings": headings,
            "word_count": self.word_count,
            "reference_count": self.reference_count,
            "source_path": self.source_path,
            "article_type": self.article_type,
        }

HEADING_NUMBER_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s*")
REF_LINE_RE = re.compile(r"(?m)^\s*(?:\[\d+\]|\d+\.)\s+")
REF_BRACKET_RE = re.compile(r"\[\d+\]")
OPENALEX_WORK_RE = re.compile(r"(?:https?://openalex\.org/)?W\d+", re.I)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s;,]+", re.I)
GENERIC_PDF_LABELS = {
    "research article",
    "review article",
    "article",
    "article in press",
    "open access",
    "view article online",
    "view journal",
    "body",
    "methodology",
    "reviewed preprint",
    "not revised",
}
JOURNAL_LINE_RE = re.compile(
    r"^(plos|bmc|elife|peerj|scientific reports|journal of|nature|frontiers|cell|the lancet|"
    r"chemcomm|chem\.?\s*commun\.?|chemical communications|royal society of chemistry)\b",
    re.I,
)
AUTHOR_LINE_RE = re.compile(
    r"(?:\b[a-z]+,\s*){1,}[a-z]+|\bet al\.?\b|\borcid\b|@|affiliat|department|university|institute|\bgoecksj@|roles\b",
    re.I,
)
TITLE_STOP_RE = re.compile(r"^(abstract|introduction|background|results|methods|references)\b", re.I)
PDF_METADATA_RE = re.compile(
    r"^(type|published|doi|received|accepted|submitted|edited by|reviewed by|correspondence|for correspondence|"
    r"competing interests|funding|reviewing editor|cite this article|from the|view article online|view journal|"
    r"creative commons|open access article|arxiv:)\b|^cite this:|@|https?://",
    re.I,
)
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
ABSTRACT_TRIM_MARKERS = (
    "author summary",
    "citation:",
    "editor:",
    "received:",
    "accepted:",
    "published:",
    "copyright:",
    "data availability statement:",
    "funding:",
    "plos genetics",
    "plos one",
    "plos computational biology",
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


def _extract_references(text: str | None) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if REF_LINE_RE.match(line) and current:
            out.append(" ".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        out.append(" ".join(current).strip())

    if len(out) <= 1:
        found = OPENALEX_WORK_RE.findall(text) or DOI_RE.findall(text)
        if found:
            return [ref.strip().rstrip(".") for ref in found]
    return [ref for ref in out if ref]


def _clean_abstract_text(text: str | None) -> str | None:
    if not text:
        return text
    lowered = text.lower()
    cut = len(text)
    for marker in ABSTRACT_TRIM_MARKERS:
        idx = lowered.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    cleaned = text[:cut].strip()
    return cleaned or text.strip()


def _clean_pdf_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00ad", "").strip())


def _infer_article_type(lines: list[str]) -> str | None:
    text = " ".join(_clean_pdf_line(line).casefold() for line in lines[:40])
    if "review article" in text or "this review" in text:
        return "review"
    if "systematic review" in text or "meta-analysis" in text:
        return "review"
    if "research article" in text or "original research" in text:
        return "original_research"
    return None


def _is_generic_pdf_label(text: str) -> bool:
    t = _clean_pdf_line(text).lower()
    if not t:
        return True
    if len(t) <= 2:
        return True
    if t in GENERIC_PDF_LABELS:
        return True
    if JOURNAL_LINE_RE.match(t):
        return True
    return False


def _looks_like_author_line(text: str) -> bool:
    t = _clean_pdf_line(text)
    if not t:
        return False
    if TITLE_STOP_RE.match(t):
        return True
    if AUTHOR_LINE_RE.search(t):
        return True
    if re.search(r"\d", t) and len(t.split()) > 3:
        return True
    return False


def _pick_pdf_title_and_authors(lines: list[str]) -> tuple[str, list[str]]:
    cleaned = [_clean_pdf_line(line) for line in lines if _clean_pdf_line(line)]
    if not cleaned:
        return "", []

    start = 0
    while start < len(cleaned) and _is_generic_pdf_label(cleaned[start]):
        start += 1

    title_parts: list[str] = []
    idx = start
    while idx < len(cleaned):
        line = cleaned[idx]
        if _is_generic_pdf_label(line):
            idx += 1
            continue
        if _looks_like_author_line(line) and title_parts:
            break
        if TITLE_STOP_RE.match(line):
            break
        title_parts.append(line)
        idx += 1
        if len(title_parts) >= 4:
            break

    title = " ".join(title_parts).strip()
    authors: list[str] = []
    while idx < len(cleaned):
        line = cleaned[idx]
        if TITLE_STOP_RE.match(line):
            break
        if _is_generic_pdf_label(line):
            idx += 1
            continue
        if re.search(r"affiliat|department|university|institute|received:|published:|doi", line, re.I):
            break
        authors.append(line)
        idx += 1
        if len(authors) >= 3:
            break
    return title or (cleaned[0] if cleaned else ""), authors


def _pick_pdf_title_from_layout(rows: list[tuple[float, float, str]]) -> str:
    candidates: list[tuple[float, float, str]] = []
    for y, size, text in rows:
        clean = _clean_pdf_line(text)
        if not clean:
            continue
        if y > 360 or size < 13:
            continue
        if _is_generic_pdf_label(clean) or PDF_METADATA_RE.search(clean):
            continue
        if TITLE_STOP_RE.match(clean):
            continue
        candidates.append((y, size, clean))
    if not candidates:
        return ""

    largest = max(size for _, size, _ in candidates)
    title_rows = [(y, size, text) for y, size, text in candidates if size >= largest - 2.5]
    title_rows.sort(key=lambda row: row[0])
    if title_rows:
        last_y = max(y for y, _, _ in title_rows)
        for y, size, text in sorted(candidates, key=lambda row: row[0]):
            if y <= last_y or y - last_y > 35:
                continue
            if size < largest - 7.5:
                continue
            if len(text.split()) < 4:
                continue
            title_rows.append((y, size, text))
            last_y = y
    title = _clean_pdf_line(" ".join(text for _, _, text in title_rows))
    if len(title.split()) >= 3:
        return title
    return ""


def _extract_pdf_abstract_from_first_page(lines: list[str], title: str) -> str | None:
    cleaned = [_clean_pdf_line(line) for line in lines if _clean_pdf_line(line)]
    if not cleaned:
        return None
    title_tokens = set(re.findall(r"[a-z0-9]+", title.casefold()))
    passed_title = False
    passed_authors = False
    out: list[str] = []
    for line in cleaned:
        lower = line.casefold()
        line_tokens = set(re.findall(r"[a-z0-9]+", lower))
        if not passed_title:
            if title_tokens and len(title_tokens & line_tokens) >= min(4, len(title_tokens)):
                passed_title = True
            continue
        if TITLE_STOP_RE.match(line):
            break
        if _is_generic_pdf_label(line) or PDF_METADATA_RE.search(line):
            continue
        if not passed_authors:
            if _looks_like_author_line(line):
                passed_authors = True
            continue
        if _looks_like_author_line(line):
            continue
        out.append(line)
        if len(" ".join(out).split()) >= 80:
            break
    abstract = _clean_abstract_text(" ".join(out).strip())
    return abstract if abstract and len(abstract.split()) >= 25 else None


def _extract_pdf_abstract_from_layout(rows: list[tuple[float, float, str]], title: str) -> str | None:
    title_tokens = set(re.findall(r"[a-z0-9]+", title.casefold()))
    title_bottom = 0.0
    for y, size, text in rows:
        if y > 260 or size < 12:
            continue
        clean = _clean_pdf_line(text)
        line_tokens = set(re.findall(r"[a-z0-9]+", clean.casefold()))
        if title_tokens and len(title_tokens & line_tokens) >= min(4, len(title_tokens)):
            title_bottom = max(title_bottom, y)
    if not title_bottom:
        return None

    out: list[str] = []
    for y, size, text in sorted(rows, key=lambda row: row[0]):
        clean = _clean_pdf_line(text)
        if y <= title_bottom + 18 or y > 520:
            continue
        if not clean or size > 11:
            continue
        if TITLE_STOP_RE.match(clean):
            break
        if _is_generic_pdf_label(clean) or PDF_METADATA_RE.search(clean) or "rsc.li/" in clean.casefold():
            continue
        if y < title_bottom + 45 and AUTHOR_LINE_RE.search(clean):
            continue
        if re.match(r"^[*a-z\d,\s]+$", clean, re.I) and len(clean.split()) <= 5:
            continue
        out.append(clean)
        if len(" ".join(out).split()) >= 120:
            break
    abstract = _clean_abstract_text(" ".join(out).strip())
    return abstract if abstract and len(abstract.split()) >= 25 else None

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
    abstract = _clean_abstract_text(abstract)
    refs_section = next((s for s in sections if _is_reference_heading(s.heading)), None)
    ref_count = _count_references(refs_section.text) if refs_section else 0
    references = _extract_references(refs_section.text if refs_section else None)
    all_text = " ".join(s.text for s in sections)
    wc = len(all_text.split())
    article_type = _infer_article_type([style for style, _ in paras] + [text for _, text in paras[:20]])
    return Manuscript(title.strip(), authors, abstract, sections, wc, ref_count, str(path), references=references, article_type=article_type)

def _parse_pdf(path: Path) -> Manuscript:
    import fitz
    doc = fitz.open(str(path))
    pages = [page.get_text("text") for page in doc]
    full = "\n".join(pages)
    if len(full.strip()) < 50:
        from .ocr import ocr_pdf
        full = ocr_pdf(path)
    lines = [l for l in full.splitlines() if l.strip()]
    first_page_lines = [l for l in pages[0].splitlines() if l.strip()] if pages else lines
    title, authors = _pick_pdf_title_and_authors(first_page_lines)
    layout_rows: list[tuple[float, float, str]] = []
    if pages:
        for block in doc[0].get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                text = " ".join(span.get("text", "").strip() for span in line.get("spans", []) if span.get("text", "").strip())
                if not text:
                    continue
                size = max((span.get("size", 0.0) for span in line.get("spans", [])), default=0.0)
                y = line.get("bbox", [0.0, 0.0, 0.0, 0.0])[1]
                layout_rows.append((float(y), float(size), text))
        layout_title = _pick_pdf_title_from_layout(layout_rows)
        if layout_title:
            title = layout_title
    if not authors:
        for authors_line in first_page_lines[1:12]:
            if _is_generic_pdf_label(authors_line) or PDF_METADATA_RE.search(authors_line):
                continue
            if not _looks_like_author_line(authors_line):
                continue
            authors = [a.strip() for a in re.split(r",| and ", authors_line) if a.strip() and len(a.strip()) < 60]
            if authors:
                break
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
    abstract = _clean_abstract_text(abstract)
    if not abstract and layout_rows:
        abstract = _extract_pdf_abstract_from_layout(layout_rows, title)
    if not abstract:
        abstract = _extract_pdf_abstract_from_first_page(first_page_lines, title)
    refs_section = next((s for s in sections if _is_reference_heading(s.heading)), None)
    ref_count = _count_references(refs_section.text) if refs_section else 0
    references = _extract_references(refs_section.text if refs_section else None)
    wc = len(full.split())
    article_type = _infer_article_type(first_page_lines)
    return Manuscript(title.strip(), authors, abstract, sections, wc, ref_count, str(path), references=references, article_type=article_type)

def parse_manuscript(path: str | Path) -> Manuscript:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".docx"}:
        return _parse_docx(p)
    if suffix == ".pdf":
        return _parse_pdf(p)
    raise ValueError(f"Unsupported extension: {suffix}")
