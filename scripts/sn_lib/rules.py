from __future__ import annotations

import re
from html import unescape
from dataclasses import asdict, dataclass, field

import httpx

from .cache import HttpCache
from .cli import emit_json
from .config import Config
from .rules_cache import RulesCache


DEFAULT_MAX_AGE_DAYS = 45


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
    cache_status: str | None = None
    fetched_at: float | None = None
    content_hash: str | None = None
    fetch_method: str | None = None
    cache_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_WORD_LIMIT_PATTERNS = (
    re.compile(r"main text should be no more than ([\d,]{3,6}) words", re.I),
    re.compile(r"manuscripts? (?:must|should) (?:not exceed|be no more than|be up to) ([\d,]{3,6}) words", re.I),
    re.compile(r"article text (?:must|should) (?:not exceed|be no more than|be up to) ([\d,]{3,6}) words", re.I),
)
_NO_WORD_LIMIT = re.compile(r"(?:no restrictions on word count|manuscripts can be any length|do not impose strict limits on word count)", re.I)
_ABSTRACT_LIMIT_PATTERNS = (
    re.compile(r"abstract (?:should|must) (?:be )?(?:no more than|not exceed|up to) ([\d,]{2,4}) words", re.I),
    re.compile(r"abstract[^.]{0,80}?(?:no more than|not exceed|up to) ([\d,]{2,4}) words", re.I),
)
_DPI = re.compile(r"([\d,]{3,5})\s*dpi", re.I)
_FORMATS = re.compile(r"\b(TIFF?|EPS|PDF|PNG|JPE?G|SVG)\b", re.I)
_REF_STYLE = re.compile(r"\b(vancouver|harvard|apa|chicago|ieee|ama|nature)\b", re.I)
_REF_LIMIT = re.compile(r"(?:max(?:imum)?|no\s+more\s+than|up\s+to|limit(?:ed)?\s+to)\s+(\d{1,3})\s+references", re.I)
_DISPLAY_ITEM_LIMIT = re.compile(r"display items are limited to (\d{1,2})", re.I)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"</(?:p|li|tr|td|h[1-6]|div)>", ". ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _clean_int(value: str) -> int:
    return int(value.replace(",", ""))


def _extract_word_limit(text: str) -> int | None:
    for pattern in _WORD_LIMIT_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean_int(match.group(1))
    if _NO_WORD_LIMIT.search(text):
        return None
    return None


def _extract_abstract_limit(text: str) -> int | None:
    for pattern in _ABSTRACT_LIMIT_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean_int(match.group(1))
    match = re.search(r"abstract should:.{0,500}?not exceed ([\d,]{2,4}) words", text, flags=re.I)
    if match:
        return _clean_int(match.group(1))
    return None


def _extract_reference_style(text: str) -> str | None:
    lowered = text.lower()
    if "free reference style" in lowered or "references may be submitted in any style or format" in lowered:
        return "free"
    if "one of two reference styles" in lowered and "harvard" in lowered and "vancouver" in lowered:
        return "harvard/vancouver"
    if "standard nature referencing style" in lowered or "nature referencing style" in lowered:
        return "nature"
    match = _REF_STYLE.search(text)
    return match.group(1).lower() if match else None


def _get(url: str, refresh: bool = False) -> str:
    cfg = Config.load()
    cache = HttpCache(cfg.cache_dir / "http.db")
    if not refresh:
        hit = cache.get(url, {"kind": "html"})
        if hit is not None:
            return hit["html"]
    r = httpx.get(url, timeout=20, follow_redirects=True)
    r.raise_for_status()
    cache.set(url, {"kind": "html"}, {"html": r.text})
    return r.text


def _extract_rules(journal: str, url: str, html: str) -> JournalRules:
    text = _strip_html(html)
    rules = JournalRules(journal=journal, source_url=url)
    rules.word_limit = _extract_word_limit(text)
    rules.abstract_limit = _extract_abstract_limit(text)
    dpi_values = sorted({_clean_int(match) for match in _DPI.findall(text)})
    if dpi_values:
        rules.figure_dpi = dpi_values[0]
    rules.figure_formats = sorted({f.upper().replace("JPEG", "JPG") for f in _FORMATS.findall(text)})
    rules.reference_style = _extract_reference_style(text)
    m = _REF_LIMIT.search(text)
    if m:
        rules.reference_limit = _clean_int(m.group(1))
    m = _DISPLAY_ITEM_LIMIT.search(text)
    if m:
        rules.table_max = _clean_int(m.group(1))
    for kw in ["word", "figure", "reference", "table", "abstract"]:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if kw in sent.lower() and 20 < len(sent) < 300:
                rules.raw_excerpts.append(sent.strip())
                break
    return rules


def _hydrate_cached_rules(cache: RulesCache, cache_status: str) -> JournalRules | None:
    payload = cache.load_rules_data()
    if payload is None:
        return None
    payload = dict(payload)
    payload["cache_status"] = cache_status
    if payload.get("cache_path") is None:
        payload["cache_path"] = str(cache.cache_dir)
    return JournalRules(**payload)


def fetch_rules(
    journal: str,
    url: str,
    *,
    refresh: bool = False,
    offline: bool = False,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> JournalRules:
    cfg = Config.load()
    rules_cache = RulesCache(cfg, journal)

    if offline:
        cached = _hydrate_cached_rules(rules_cache, "stale-cache")
        if cached is not None:
            return cached
        raise FileNotFoundError(f"No cached rules available for {journal}")

    cache_is_fresh = rules_cache.is_fresh(max_age_days)
    if not refresh and cache_is_fresh:
        cached = _hydrate_cached_rules(rules_cache, "fresh-cache")
        if cached is not None:
            return cached

    try:
        html = _get(url, refresh=refresh or not cache_is_fresh)
    except httpx.HTTPError:
        cached = _hydrate_cached_rules(rules_cache, "stale-cache")
        if cached is not None:
            return cached
        raise

    rules = _extract_rules(journal, url, html)
    rules_cache.save(rules.to_dict(), html, url, fetch_method="httpx")
    cached = _hydrate_cached_rules(rules_cache, "fresh-fetch")
    return cached or rules
