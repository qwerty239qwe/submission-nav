from __future__ import annotations
import httpx
from dataclasses import dataclass, asdict
from .config import Config
from .cache import HttpCache

OPENALEX_SOURCES = "https://api.openalex.org/sources"
CROSSREF_JOURNALS = "https://api.crossref.org/journals"
DOAJ_JOURNALS = "https://doaj.org/api/search/journals"

@dataclass
class VenueHit:
    id: str
    name: str
    issn: str | None
    publisher: str | None
    is_oa: bool | None
    apc_usd: float | None
    impact_proxy: float | None
    h_index: int | None
    concepts: list[str]
    source: str

    def to_dict(self) -> dict:
        return asdict(self)

def _cache() -> HttpCache:
    cfg = Config.load()
    return HttpCache(cfg.cache_dir / "http.db")

def _get(url: str, params: dict, headers: dict | None = None) -> dict:
    cache = _cache()
    hit = cache.get(url, params)
    if hit is not None:
        return hit
    r = httpx.get(url, params=params, headers=headers or {}, timeout=20)
    r.raise_for_status()
    data = r.json()
    cache.set(url, params, data)
    return data

def search_openalex(query: str, per_page: int = 25) -> list[VenueHit]:
    cfg = Config.load()
    params = {"search": query, "per-page": per_page}
    if cfg.openalex_email:
        params["mailto"] = cfg.openalex_email
    data = _get(OPENALEX_SOURCES, params)
    out: list[VenueHit] = []
    for r in data.get("results", []):
        stats = r.get("summary_stats") or {}
        out.append(VenueHit(
            id=r.get("id", ""),
            name=r.get("display_name", ""),
            issn=r.get("issn_l"),
            publisher=r.get("host_organization_name"),
            is_oa=r.get("is_oa"),
            apc_usd=r.get("apc_usd"),
            impact_proxy=stats.get("2yr_mean_citedness"),
            h_index=stats.get("h_index"),
            concepts=[c.get("display_name", "") for c in (r.get("x_concepts") or [])[:5]],
            source="openalex",
        ))
    return out

def enrich_doaj(issn: str) -> dict | None:
    if not issn:
        return None
    try:
        data = _get(f"{DOAJ_JOURNALS}/issn:{issn}", {})
    except Exception:
        return None
    results = data.get("results") or []
    return results[0] if results else None

def search_venues(query: str, per_page: int = 25) -> list[VenueHit]:
    hits = search_openalex(query, per_page=per_page)
    for h in hits:
        if h.is_oa and h.apc_usd is None and h.issn:
            d = enrich_doaj(h.issn)
            if d:
                bib = d.get("bibjson", {})
                apc = (bib.get("apc") or {}).get("max") or []
                if apc:
                    h.apc_usd = apc[0].get("price")
    return hits

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--per-page", type=int, default=25)
    args = ap.parse_args()
    hits = search_venues(args.query, per_page=args.per_page)
    print(json.dumps([h.to_dict() for h in hits], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
