from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from difflib import SequenceMatcher

from .config import Config
from .venues import VenueHit


RISK_FILENAME = "publisher_risk.json"
RISK_LABELS = {
    "trusted": 1.0,
    "unknown": 0.85,
    "caution": 0.60,
    "potential_predatory_match": 0.20,
    "hijacked_or_identity_risk": 0.0,
}
TRUSTED_PUBLISHERS = {
    "american association for the advancement of science",
    "american college of medical genetics and genomics",
    "american society for microbiology",
    "annual reviews",
    "bio-protocol",
    "biomed central",
    "bmj",
    "cambridge university press",
    "cell press",
    "elsevier",
    "elsevier bv",
    "frontiers media",
    "ieee",
    "mdpi",
    "nature portfolio",
    "oxford university press",
    "plos",
    "public library of science",
    "sage publications",
    "springer",
    "springer nature",
    "taylor & francis",
    "wiley",
    "wiley-blackwell",
}


@dataclass(frozen=True)
class PublisherRisk:
    label: str
    fit: float
    reasons: tuple[str, ...]
    sources: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "fit": round(self.fit, 3),
            "reasons": list(self.reasons),
            "sources": list(self.sources),
        }


def _norm(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("&", " and ").split())


def _risk_path() -> Path:
    return Config.load().config_dir / RISK_FILENAME


def _load_local_risk_lists() -> dict[str, list[str]]:
    path = _risk_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in data.items():
        if isinstance(value, list):
            out[key] = [str(item) for item in value if str(item).strip()]
    return out


def _match_any(value: str, candidates: list[str]) -> bool:
    if not value:
        return False
    for candidate in candidates:
        normalized = _norm(candidate)
        if not normalized:
            continue
        if value == normalized:
            return True
        if SequenceMatcher(None, value, normalized).ratio() >= 0.96:
            return True
    return False


def assess_publisher_risk(venue: VenueHit) -> PublisherRisk:
    name = _norm(venue.name)
    publisher = _norm(venue.publisher)
    source_parts = set((venue.source or "").split("+"))
    risk_lists = _load_local_risk_lists()
    reasons: list[str] = []
    sources: list[str] = []

    if _match_any(name, risk_lists.get("hijacked_journals", [])):
        return PublisherRisk(
            "hijacked_or_identity_risk",
            RISK_LABELS["hijacked_or_identity_risk"],
            ("journal matches local hijacked/identity-risk list",),
            ("local_publisher_risk",),
        )

    if _match_any(publisher, risk_lists.get("potential_predatory_publishers", [])):
        return PublisherRisk(
            "potential_predatory_match",
            RISK_LABELS["potential_predatory_match"],
            ("publisher matches local potential-predatory list",),
            ("local_publisher_risk",),
        )

    if _match_any(name, risk_lists.get("potential_predatory_journals", [])):
        return PublisherRisk(
            "potential_predatory_match",
            RISK_LABELS["potential_predatory_match"],
            ("journal matches local potential-predatory list",),
            ("local_publisher_risk",),
        )

    if _match_any(publisher, risk_lists.get("trusted_publishers", [])) or publisher in TRUSTED_PUBLISHERS:
        reasons.append("publisher appears in trusted publisher signals")
        sources.append("trusted_publisher")

    if "doaj" in source_parts:
        reasons.append("journal has DOAJ enrichment signal")
        sources.append("doaj")
    if "scopus" in source_parts:
        reasons.append("journal has Scopus/Elsevier serial metadata signal")
        sources.append("scopus")
    if "dblp" in source_parts and venue.venue_type == "conference":
        reasons.append("conference has DBLP venue metadata signal")
        sources.append("dblp")

    if sources:
        return PublisherRisk("trusted", RISK_LABELS["trusted"], tuple(reasons), tuple(sources))

    if not publisher:
        return PublisherRisk(
            "caution",
            RISK_LABELS["caution"],
            ("publisher is missing; verify journal identity before submission",),
            (),
        )

    if venue.is_oa is True and venue.apc_usd and not ({"doaj", "scopus"} & source_parts):
        return PublisherRisk(
            "caution",
            RISK_LABELS["caution"],
            ("OA/APC venue lacks DOAJ or Scopus enrichment signal; verify publisher carefully",),
            (),
        )

    return PublisherRisk(
        "unknown",
        RISK_LABELS["unknown"],
        ("publisher integrity not verified by local risk list or strong indexing signal",),
        (),
    )
