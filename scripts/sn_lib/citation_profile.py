from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass

import httpx
from rapidfuzz import fuzz

from .cache import HttpCache
from .config import Config
from .venues import OPENALEX_WORKS, VenueHit


OPENALEX_WORK_ID_RE = re.compile(r"(?:https?://openalex\.org/)?(W\d+)", re.I)
SOURCE_WEIGHT = 0.45
TOPIC_WEIGHT = 0.40
FIELD_WEIGHT = 0.15


@dataclass
class CitationProfile:
    source_counts: dict[str, float]
    topic_counts: dict[str, float]
    field_counts: dict[str, float]
    resolved_refs: int
    unresolved_refs: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict | None) -> "CitationProfile | None":
        if not payload:
            return None
        return cls(
            source_counts=dict(payload.get("source_counts") or {}),
            topic_counts=dict(payload.get("topic_counts") or {}),
            field_counts=dict(payload.get("field_counts") or {}),
            resolved_refs=int(payload.get("resolved_refs") or 0),
            unresolved_refs=int(payload.get("unresolved_refs") or 0),
        )


def normalize_token(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip() if value else ""


def extract_openalex_work_ids(references: list[str], max_refs: int = 30) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for ref in references:
        for match in OPENALEX_WORK_ID_RE.findall(ref or ""):
            work_id = match.upper()
            if work_id in seen:
                continue
            seen.add(work_id)
            out.append(work_id)
            if len(out) >= max_refs:
                return out
    return out


def _cache() -> HttpCache:
    cfg = Config.load()
    return HttpCache(cfg.cache_dir / "http.db")


def _get_openalex_work(work_id: str) -> dict | None:
    url = f"{OPENALEX_WORKS}/{work_id}"
    params: dict[str, str] = {}
    mailto = Config.load().key("openalex_email")
    if mailto:
        params["mailto"] = mailto
    cache = _cache()
    cached = cache.get(url, params)
    if cached is not None:
        return cached
    try:
        response = httpx.get(url, params=params, timeout=20)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    data = response.json()
    cache.set(url, params, data)
    return data


def _nested_get(data: dict, *path: str):
    cur = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _add(counter: Counter[str], value: str | None, weight: float = 1.0) -> None:
    key = normalize_token(value)
    if key:
        counter[key] += weight


def _source_terms(work: dict) -> list[str]:
    source = _nested_get(work, "primary_location", "source") or {}
    terms = [
        source.get("id"),
        source.get("display_name"),
        source.get("issn_l"),
    ]
    terms.extend(source.get("issn") or [])
    return [term for term in terms if term]


def _topic_terms(work: dict) -> tuple[list[str], list[str]]:
    topics: list[str] = []
    fields: list[str] = []
    for path in (
        ("primary_topic", "display_name"),
        ("primary_topic", "subfield", "display_name"),
    ):
        value = _nested_get(work, *path)
        if value:
            topics.append(value)
    for path in (
        ("primary_topic", "field", "display_name"),
        ("primary_topic", "domain", "display_name"),
    ):
        value = _nested_get(work, *path)
        if value:
            fields.append(value)
    for topic in work.get("topics") or []:
        if not isinstance(topic, dict):
            continue
        if topic.get("display_name"):
            topics.append(topic["display_name"])
        for path in (("subfield", "display_name"), ("field", "display_name"), ("domain", "display_name")):
            value = _nested_get(topic, *path)
            if value:
                fields.append(value)
    return topics, fields


def build_citation_profile(reference_works: list[dict], unresolved_refs: int = 0) -> CitationProfile:
    source_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    for work in reference_works:
        for term in _source_terms(work):
            _add(source_counts, term)
        topics, fields = _topic_terms(work)
        for term in topics:
            _add(topic_counts, term)
        for term in fields:
            _add(field_counts, term)
    resolved = len(reference_works)
    return CitationProfile(
        source_counts=dict(source_counts),
        topic_counts=dict(topic_counts),
        field_counts=dict(field_counts),
        resolved_refs=resolved,
        unresolved_refs=unresolved_refs,
    )


def build_citation_profile_from_references(references: list[str], max_refs: int = 30) -> CitationProfile | None:
    work_ids = extract_openalex_work_ids(references, max_refs=max_refs)
    if not work_ids:
        return None
    works = []
    for work_id in work_ids:
        work = _get_openalex_work(work_id)
        if work:
            works.append(work)
    return build_citation_profile(works, unresolved_refs=max(0, len(work_ids) - len(works)))


def _best_weighted_fuzzy(needles: dict[str, float], haystack: list[str], threshold: int = 82) -> float:
    if not needles or not haystack:
        return 0.0
    total = sum(max(0.0, weight) for weight in needles.values())
    if total <= 0:
        return 0.0
    matched = 0.0
    normalized_haystack = [normalize_token(item) for item in haystack if normalize_token(item)]
    for needle, weight in needles.items():
        best = max((fuzz.token_set_ratio(needle, item) for item in normalized_haystack), default=0)
        if best >= threshold:
            matched += weight * (best / 100.0)
    return min(1.0, matched / total)


def score_citation_relatedness(profile: CitationProfile | dict | None, venue: VenueHit) -> dict:
    if isinstance(profile, dict):
        profile = CitationProfile.from_dict(profile)
    if profile is None or profile.resolved_refs == 0:
        return {"score": 0.0, "reasons": ["no resolved reference profile"], "resolved_refs": 0}

    venue_terms = [
        venue.id,
        venue.name,
        venue.issn,
        venue.publisher,
        *(venue.concepts or []),
    ]
    source_score = _best_weighted_fuzzy(profile.source_counts, [venue.id, venue.name, venue.issn or ""], threshold=90)
    topic_score = _best_weighted_fuzzy(profile.topic_counts, venue_terms, threshold=78)
    field_score = _best_weighted_fuzzy(profile.field_counts, venue_terms, threshold=82)
    score = SOURCE_WEIGHT * source_score + TOPIC_WEIGHT * topic_score + FIELD_WEIGHT * field_score
    if profile.resolved_refs < 5:
        score *= 0.75
    score = min(1.0, score)

    reasons = [
        f"resolved_refs={profile.resolved_refs}",
        f"source_overlap={source_score:.2f}",
        f"topic_overlap={topic_score:.2f}",
        f"field_overlap={field_score:.2f}",
    ]
    if profile.unresolved_refs:
        reasons.append(f"unresolved_refs={profile.unresolved_refs}")
    return {"score": round(score, 4), "reasons": reasons, "resolved_refs": profile.resolved_refs}
