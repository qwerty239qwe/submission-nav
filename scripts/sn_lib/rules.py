from __future__ import annotations

import re
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


_WORD_LIMIT = re.compile(r"(?:not\s+exceed|max(?:imum)?|limit(?:ed)?\s+to|up\s+to)\s+(\d{3,5})\s+words", re.I)
_ABSTRACT_LIMIT = re.compile(r"abstract[^.]{0,80}?(\d{2,4})\s+words", re.I)
_DPI = re.compile(r"(\d{3,4})\s*dpi", re.I)
_FORMATS = re.compile(r"\b(TIFF?|EPS|PDF|PNG|JPE?G|SVG)\b", re.I)
_REF_STYLE = re.compile(r"\b(vancouver|harvard|apa|chicago|ieee|ama)\b", re.I)
_REF_LIMIT = re.compile(r"(?:max(?:imum)?|no\s+more\s+than|up\s+to|limit(?:ed)?\s+to)\s+(\d{1,3})\s+references", re.I)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def _main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("journal")
    ap.add_argument("url")
    ap.add_argument("--out", help="Optional path to write JSON output.")
    ap.add_argument("--refresh", action="store_true", help="Refresh cached rules from the source URL.")
    ap.add_argument("--offline", action="store_true", help="Use only locally cached rules.")
    ap.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS, help="Maximum cache age before refresh is attempted.")
    args = ap.parse_args()
    r = fetch_rules(
        args.journal,
        args.url,
        refresh=args.refresh,
        offline=args.offline,
        max_age_days=args.max_age_days,
    )
    emit_json(r.to_dict(), args.out)


if __name__ == "__main__":
    _main()
