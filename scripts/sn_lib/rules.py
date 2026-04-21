from __future__ import annotations
import re, httpx
from dataclasses import dataclass, asdict, field
from .cache import HttpCache
from .config import Config

@dataclass
class JournalRules:
    journal: str
    source_url: str
    word_limit: int | None = None
    abstract_limit: int | None = None
    figure_dpi: int | None = None
    figure_formats: list[str] = field(default_factory=list)
    table_max: int | None = None
    reference_style: str | None = None
    reference_limit: int | None = None
    raw_excerpts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

_WORD_LIMIT = re.compile(r"(?:not\s+exceed|max(?:imum)?|limit(?:ed)?\s+to|up\s+to)\s+(\d{3,5})\s+words", re.I)
_ABSTRACT_LIMIT = re.compile(r"abstract[^.]{0,60}?(\d{2,4})\s+words", re.I)
_DPI = re.compile(r"(\d{3,4})\s*dpi", re.I)
_FORMATS = re.compile(r"\b(TIFF?|EPS|PDF|PNG|JPE?G|SVG)\b", re.I)
_REF_STYLE = re.compile(r"\b(vancouver|harvard|apa|chicago|ieee|ama)\b", re.I)
_REF_LIMIT = re.compile(r"(?:max(?:imum)?|no\s+more\s+than|up\s+to|limit(?:ed)?\s+to)\s+(\d{1,3})\s+references", re.I)

def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _get(url: str) -> str:
    cfg = Config.load()
    cache = HttpCache(cfg.cache_dir / "http.db")
    hit = cache.get(url, {"kind": "html"})
    if hit is not None:
        return hit["html"]
    r = httpx.get(url, timeout=20, follow_redirects=True)
    r.raise_for_status()
    cache.set(url, {"kind": "html"}, {"html": r.text})
    return r.text

def fetch_rules(journal: str, url: str) -> JournalRules:
    html = _get(url)
    text = _strip_html(html)
    rules = JournalRules(journal=journal, source_url=url)
    m = _WORD_LIMIT.search(text)
    if m:
        rules.word_limit = int(m.group(1))
    m = _ABSTRACT_LIMIT.search(text)
    if m:
        rules.abstract_limit = int(m.group(1))
    m = _DPI.search(text)
    if m:
        rules.figure_dpi = int(m.group(1))
    rules.figure_formats = sorted({f.upper().replace("JPEG", "JPG") for f in _FORMATS.findall(text)})
    m = _REF_STYLE.search(text)
    if m:
        rules.reference_style = m.group(1).lower()
    m = _REF_LIMIT.search(text)
    if m:
        rules.reference_limit = int(m.group(1))
    for kw in ["word", "figure", "reference", "table", "abstract"]:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if kw in sent.lower() and 20 < len(sent) < 300:
                rules.raw_excerpts.append(sent.strip())
                break
    return rules

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("journal")
    ap.add_argument("url")
    args = ap.parse_args()
    r = fetch_rules(args.journal, args.url)
    print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
