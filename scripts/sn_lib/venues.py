from __future__ import annotations
import httpx
import time
from dataclasses import dataclass, asdict
from rapidfuzz import fuzz
from .cli import emit_json
from .config import Config
from .cache import HttpCache

OPENALEX_SOURCES = "https://api.openalex.org/sources"
OPENALEX_WORKS = "https://api.openalex.org/works"
CROSSREF_JOURNALS = "https://api.crossref.org/journals"
DBLP_VENUES = "https://dblp.org/search/venue/api"
DOAJ_JOURNALS = "https://doaj.org/api/search/journals"
SCOPUS_SERIAL_TITLE = "https://api.elsevier.com/content/serial/title"
ELSEVIER_SERIAL_TITLE_FIELDS = "dc:title,prism:publicationName,SJR,SNIP"
ELSEVIER_REQUESTS_PER_SECOND = 6
ELSEVIER_MIN_INTERVAL_SECONDS = 1.0 / ELSEVIER_REQUESTS_PER_SECOND
ELSEVIER_ENRICH_TOP_N = 10
DBLP_ENRICH_TOP_N = 20
NEIGHBOR_EXPAND_SEEDS = 4
NEIGHBOR_EXPAND_PER_SEED = 12
_last_elsevier_request_ts = 0.0

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
    venue_type: str | None = None
    evidence_count: int = 0
    dblp_acronym: str | None = None
    dblp_url: str | None = None
    dblp_type: str | None = None
    specialty_domain: str | None = None
    specialty_confidence: float | None = None

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


def _type_filter(venue_types: tuple[str, ...]) -> str:
    filtered = [t for t in venue_types if t]
    if not filtered:
        filtered = ["journal"]
    return "|".join(filtered)


def _throttle_elsevier() -> None:
    global _last_elsevier_request_ts
    now = time.monotonic()
    wait = ELSEVIER_MIN_INTERVAL_SECONDS - (now - _last_elsevier_request_ts)
    if wait > 0:
        time.sleep(wait)
        now = time.monotonic()
    _last_elsevier_request_ts = now

def search_openalex(query: str, per_page: int = 25, venue_types: tuple[str, ...] = ("journal",)) -> list[VenueHit]:
    params = {"search": query, "per-page": per_page, "filter": f"type:{_type_filter(venue_types)}"}
    openalex_mailto = Config.load().key("openalex_email")
    if openalex_mailto:
        params["mailto"] = openalex_mailto
    data = _get(OPENALEX_SOURCES, params)
    out: list[VenueHit] = []
    for r in data.get("results", []):
        stats = r.get("summary_stats") or {}
        out.append(VenueHit(
            id=r.get("id", ""),
            name=r.get("display_name", ""),
            issn=r.get("issn_l"),
            publisher=r.get("host_organization_name"),
            venue_type=r.get("type") or "journal",
            is_oa=r.get("is_oa"),
            apc_usd=r.get("apc_usd"),
            impact_proxy=stats.get("2yr_mean_citedness"),
            h_index=stats.get("h_index"),
            concepts=[c.get("display_name", "") for c in (r.get("x_concepts") or [])[:5]],
            source="openalex",
            evidence_count=0,
        ))
    return out


def _nested_get(data: dict, *path):
    cur = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def search_openalex_by_works(query: str, per_page: int = 50, venue_types: tuple[str, ...] = ("journal",)) -> list[VenueHit]:
    params = {
        "search": query,
        "filter": f"primary_location.source.type:{_type_filter(venue_types)}",
        "per-page": min(per_page, 200),
    }
    openalex_mailto = Config.load().key("openalex_email")
    if openalex_mailto:
        params["mailto"] = openalex_mailto
    try:
        data = _get(OPENALEX_WORKS, params)
    except httpx.HTTPStatusError:
        return []
    grouped: dict[str, dict] = {}
    for work in data.get("results", []):
        source = _nested_get(work, "primary_location", "source") or {}
        source_id = source.get("id")
        if not source_id:
            continue
        row = grouped.setdefault(source_id, {
            "id": source_id,
            "name": source.get("display_name", ""),
            "issn": source.get("issn_l"),
            "publisher": source.get("host_organization_name"),
            "venue_type": source.get("type") or "journal",
            "is_oa": source.get("is_oa"),
            "apc_usd": None,
            "impact_proxy": None,
            "h_index": None,
            "concepts": [],
            "source": "openalex-works",
            "evidence_count": 0,
        })
        row["evidence_count"] += 1
        for topic_path in (
            ("primary_topic", "display_name"),
            ("primary_topic", "subfield", "display_name"),
            ("primary_topic", "field", "display_name"),
            ("primary_topic", "domain", "display_name"),
        ):
            display_name = _nested_get(work, *topic_path)
            if display_name and display_name not in row["concepts"]:
                row["concepts"].append(display_name)
        for topic in work.get("topics") or []:
            display_name = topic.get("display_name")
            if display_name and display_name not in row["concepts"]:
                row["concepts"].append(display_name)
        for key, fallback in (
            ("name", source.get("display_name", "")),
            ("issn", source.get("issn_l")),
            ("publisher", source.get("host_organization_name")),
            ("venue_type", source.get("type") or "journal"),
            ("is_oa", source.get("is_oa")),
        ):
            if not row[key] and fallback:
                row[key] = fallback
    hits = [VenueHit(**row) for row in grouped.values()]
    max_evidence = max((hit.evidence_count for hit in hits), default=0)
    for hit in hits:
        if hit.evidence_count >= 2:
            hit.specialty_domain = "similar_works"
            hit.specialty_confidence = min(0.90, 0.42 + 0.12 * hit.evidence_count)
        elif max_evidence == 1 and hit.evidence_count == 1:
            hit.specialty_domain = "similar_works"
            hit.specialty_confidence = 0.38
    return hits


def _query_tokens(query: str) -> set[str]:
    stop = {
        "journal", "research", "study", "using", "based", "analysis", "method", "methods",
        "data", "model", "models", "effect", "effects", "paper", "the", "and", "for",
    }
    return {token for token in re_split_words(query) if token not in stop and len(token) > 2}


def _ordered_query_tokens(query: str) -> list[str]:
    tokens = _query_tokens(query)
    return [token for token in re_split_words(query) if token in tokens]


def re_split_words(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", (text or "").casefold())


def _source_specialty_confidence(query: str, hit: VenueHit) -> float:
    tokens = _query_tokens(query)
    if not tokens:
        return 0.0
    haystack = " ".join([hit.name or "", " ".join(hit.concepts)]).casefold()
    matched = sum(1 for token in tokens if token in haystack)
    if matched == 0:
        return 0.0
    return min(0.55, matched / max(len(tokens), 1) * 0.55)


def _neighbor_queries(query: str, hits: list[VenueHit], limit: int = NEIGHBOR_EXPAND_SEEDS) -> list[str]:
    query_terms = _ordered_query_tokens(query)[:4]
    out: list[str] = []
    ranked = sorted(
        hits,
        key=lambda h: (h.evidence_count, h.specialty_confidence or 0.0, h.impact_proxy or 0.0, h.h_index or 0),
        reverse=True,
    )
    for hit in ranked:
        if len(out) >= limit:
            break
        concept_terms = []
        for concept in hit.concepts[:4]:
            clean = " ".join(_ordered_query_tokens(concept)[:4])
            if clean and clean not in concept_terms:
                concept_terms.append(clean)
        for concept in concept_terms:
            pieces = [concept]
            for term in query_terms:
                if term not in concept.split():
                    pieces.append(term)
                if len(pieces) >= 5:
                    break
            neighbor_query = " ".join(pieces).strip()
            if neighbor_query and neighbor_query not in out:
                out.append(neighbor_query)
                break
    return out


def expand_neighbor_venues(
    query: str,
    hits: list[VenueHit],
    per_seed: int = NEIGHBOR_EXPAND_PER_SEED,
    venue_types: tuple[str, ...] = ("journal",),
) -> list[VenueHit]:
    """Second-hop retrieval from first-hop venue concepts.

    OpenAlex source search is useful but often misses the exact journal that
    published similar papers. A bounded second pass through works gives the
    ranker more neighboring venues without relying on field-specific seeds.
    """
    expanded: list[VenueHit] = []
    existing_keys = {key for hit in hits for key in _hit_keys(hit)}
    for neighbor_query in _neighbor_queries(query, hits):
        for hit in search_openalex_by_works(neighbor_query, per_page=per_seed, venue_types=venue_types):
            if any(key in existing_keys for key in _hit_keys(hit)):
                continue
            hit.source = f"{hit.source}+neighbor"
            if (hit.specialty_confidence or 0.0) < 0.44:
                hit.specialty_confidence = 0.44
                hit.specialty_domain = "source_neighborhood"
            elif hit.specialty_domain == "similar_works":
                hit.specialty_domain = "source_neighborhood"
            expanded.append(hit)
            existing_keys.update(_hit_keys(hit))
    return expanded


def _hit_key(hit: VenueHit) -> str:
    if hit.issn:
        return f"issn:{hit.issn.casefold()}"
    if hit.name:
        return f"name:{hit.name.casefold().strip()}"
    return f"id:{hit.id}"


def _hit_keys(hit: VenueHit) -> list[str]:
    keys = []
    if hit.issn:
        keys.append(f"issn:{hit.issn.casefold()}")
    if hit.name:
        keys.append(f"name:{hit.name.casefold().strip()}")
    if hit.id:
        keys.append(f"id:{hit.id}")
    return keys


def _merge_hits(primary: list[VenueHit], secondary: list[VenueHit]) -> list[VenueHit]:
    merged: dict[str, VenueHit] = {}
    for hit in primary + secondary:
        keys = _hit_keys(hit)
        if not keys:
            continue
        existing = next((merged[key] for key in keys if key in merged), None)
        key = keys[0]
        if existing is None:
            for alias in keys:
                merged[alias] = hit
            continue
        existing.name = existing.name or hit.name
        existing.issn = existing.issn or hit.issn
        existing.publisher = existing.publisher or hit.publisher
        existing.venue_type = existing.venue_type or hit.venue_type
        existing.is_oa = existing.is_oa if existing.is_oa is not None else hit.is_oa
        existing.apc_usd = existing.apc_usd if existing.apc_usd is not None else hit.apc_usd
        existing.impact_proxy = existing.impact_proxy if existing.impact_proxy is not None else hit.impact_proxy
        existing.h_index = existing.h_index if existing.h_index is not None else hit.h_index
        existing.dblp_acronym = existing.dblp_acronym or hit.dblp_acronym
        existing.dblp_url = existing.dblp_url or hit.dblp_url
        existing.dblp_type = existing.dblp_type or hit.dblp_type
        if (hit.specialty_confidence or 0.0) > (existing.specialty_confidence or 0.0):
            existing.specialty_domain = hit.specialty_domain
            existing.specialty_confidence = hit.specialty_confidence
        for concept in hit.concepts:
            if concept and concept not in existing.concepts:
                existing.concepts.append(concept)
        existing.evidence_count += hit.evidence_count
        source_parts = [part for part in existing.source.split("+") if part]
        for part in hit.source.split("+"):
            if part and part not in source_parts:
                source_parts.append(part)
        existing.source = "+".join(source_parts)
        for alias in keys:
            merged[alias] = existing
    return sorted(
        {id(hit): hit for hit in merged.values()}.values(),
        key=lambda h: (h.evidence_count, h.impact_proxy or 0.0, h.h_index or 0),
        reverse=True,
    )

def enrich_scopus(issn: str) -> dict | None:
    if not issn:
        return None
    cfg = Config.load()
    scopus_key = cfg.key("scopus_key")
    if not scopus_key:
        return None
    headers = {
        "X-ELS-APIKey": scopus_key,
        "Accept": "application/json",
    }
    params = {
        "issn": issn,
        "view": "STANDARD",
        "field": ELSEVIER_SERIAL_TITLE_FIELDS,
    }
    # Respect local Elsevier usage rules: one metadata request per ISSN, rate-limited,
    # and only for top-ranked candidates in search_venues.
    _throttle_elsevier()
    try:
        return _get(SCOPUS_SERIAL_TITLE, params, headers=headers)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {400, 401, 403, 404, 429}:
            return None
        raise

def _latest_metric(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, list):
        for item in reversed(value):
            metric = _latest_metric(item)
            if metric is not None:
                return metric
        return None
    if isinstance(value, dict):
        for key in ("$", "@value", "value"):
            if key in value:
                metric = _latest_metric(value[key])
                if metric is not None:
                    return metric
        for key in ("SJR", "SNIP"):
            if key in value:
                metric = _latest_metric(value[key])
                if metric is not None:
                    return metric
        return None
    return None

def _extract_scopus_metrics(payload: dict) -> tuple[float | None, str | None]:
    root = payload.get("serial-metadata-response") or payload
    entries = root.get("entry") or []
    if isinstance(entries, dict):
        entries = [entries]
    if not entries:
        return None, None
    entry = entries[0]
    sjr = _latest_metric(entry.get("SJRList"))
    snip = _latest_metric(entry.get("SNIPList"))
    title = entry.get("dc:title") or entry.get("prism:publicationName")
    return sjr if sjr is not None else snip, title

def enrich_doaj(issn: str) -> dict | None:
    if not issn:
        return None
    cfg = Config.load()
    params: dict[str, str] = {}
    doaj_key = cfg.key("doaj_key")
    if doaj_key:
        params["api_key"] = doaj_key
    data = _get(f"{DOAJ_JOURNALS}/issn:{issn}", params)
    results = data.get("results") or []
    return results[0] if results else None


def enrich_crossref(issn: str) -> dict | None:
    if not issn:
        return None
    params: dict[str, str] = {}
    crossref_email = Config.load().key("crossref_email")
    if crossref_email:
        params["mailto"] = crossref_email
    try:
        data = _get(f"{CROSSREF_JOURNALS}/{issn}", params)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {400, 404, 429}:
            return None
        raise
    return data.get("message") or data


def _apply_crossref(hit: VenueHit, payload: dict) -> None:
    if not payload:
        return
    title = payload.get("title")
    if not hit.name and title:
        hit.name = title
    publisher = payload.get("publisher")
    if not hit.publisher and publisher:
        hit.publisher = publisher
    if not hit.issn:
        issns = payload.get("ISSN") or []
        if issns:
            hit.issn = issns[0]
    if "crossref" not in hit.source.split("+"):
        hit.source = f"{hit.source}+crossref"


def search_dblp_venues(query: str, max_hits: int = 5) -> list[dict]:
    params = {"q": query, "format": "json", "h": max_hits, "c": 0}
    try:
        data = _get(DBLP_VENUES, params)
    except httpx.HTTPError:
        return []
    hits = data.get("result", {}).get("hits", {}).get("hit") or []
    if isinstance(hits, dict):
        hits = [hits]
    out: list[dict] = []
    for hit in hits:
        info = hit.get("info") or {}
        venue = info.get("venue")
        if not venue:
            continue
        out.append({
            "venue": venue,
            "acronym": info.get("acronym"),
            "type": info.get("type"),
            "url": info.get("url"),
        })
    return out


def _apply_dblp(hit: VenueHit, payload: dict) -> None:
    hit.dblp_acronym = hit.dblp_acronym or payload.get("acronym")
    hit.dblp_url = hit.dblp_url or payload.get("url")
    hit.dblp_type = hit.dblp_type or payload.get("type")
    dblp_name = payload.get("venue")
    if dblp_name and (not hit.name or len(dblp_name) < len(hit.name)):
        hit.name = dblp_name
    if "dblp" not in hit.source.split("+"):
        hit.source = f"{hit.source}+dblp"


def enrich_dblp(hit: VenueHit) -> dict | None:
    if hit.venue_type != "conference" or not hit.name:
        return None
    candidates = search_dblp_venues(hit.name, max_hits=5)
    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda item: max(
            fuzz.token_set_ratio(hit.name, item.get("venue") or ""),
            fuzz.token_set_ratio(hit.name, item.get("acronym") or ""),
        ),
    )
    score = max(
        fuzz.token_set_ratio(hit.name, best.get("venue") or ""),
        fuzz.token_set_ratio(hit.name, best.get("acronym") or ""),
    )
    return best if score >= 72 else None


def search_venues(
    query: str,
    per_page: int = 25,
    venue_types: tuple[str, ...] = ("journal",),
    expand_neighbors: bool = False,
) -> list[VenueHit]:
    hits = _merge_hits(
        search_openalex_by_works(query, per_page=max(50, per_page), venue_types=venue_types),
        search_openalex(query, per_page=per_page, venue_types=venue_types),
    )
    for hit in hits:
        source_confidence = _source_specialty_confidence(query, hit)
        if source_confidence > (hit.specialty_confidence or 0.0):
            hit.specialty_confidence = source_confidence
            hit.specialty_domain = "source_concepts"
    if expand_neighbors:
        neighbor_hits = expand_neighbor_venues(query, hits, venue_types=venue_types)
        if neighbor_hits:
            hits = _merge_hits(hits, neighbor_hits)
    for idx, h in enumerate(hits):
        if idx >= ELSEVIER_ENRICH_TOP_N:
            break
        if h.issn:
            scopus = enrich_scopus(h.issn)
            if scopus:
                metric, title = _extract_scopus_metrics(scopus)
                if h.impact_proxy is None and metric is not None:
                    h.impact_proxy = metric
                if not h.name and title:
                    h.name = title
                if "scopus" not in h.source.split("+"):
                    h.source = f"{h.source}+scopus"
        if h.is_oa and h.apc_usd is None and h.issn:
            d = enrich_doaj(h.issn)
            if d:
                if "doaj" not in h.source.split("+"):
                    h.source = f"{h.source}+doaj"
                bib = d.get("bibjson", {})
                apc = (bib.get("apc") or {}).get("max") or []
                if apc:
                    h.apc_usd = apc[0].get("price")
        if h.issn and (not h.name or not h.publisher or "crossref" not in h.source.split("+")):
            crossref = enrich_crossref(h.issn)
            if crossref:
                _apply_crossref(h, crossref)
    for idx, h in enumerate(hits):
        if idx >= DBLP_ENRICH_TOP_N:
            break
        if h.venue_type == "conference":
            dblp = enrich_dblp(h)
            if dblp:
                _apply_dblp(h, dblp)
    return hits
