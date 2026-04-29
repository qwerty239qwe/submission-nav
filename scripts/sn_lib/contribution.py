from __future__ import annotations

import re

from .venues import VenueHit


TIER_ORDER = {
    "exploratory": 0,
    "solid_specialty": 1,
    "strong_specialty": 2,
    "high_impact_specialty": 3,
    "elite_general": 4,
}

VENUE_AMBITION_ORDER = {
    "fallback": 0,
    "safe_specialty": 1,
    "broad_megajournal": 1,
    "specialty_target": 2,
    "selective_specialty": 3,
    "high_impact_specialty": 4,
    "top_clinical": 5,
    "elite_general": 5,
}


def _norm(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _section_text(manuscript_full: dict | None) -> str:
    if not manuscript_full:
        return ""
    sections = manuscript_full.get("sections") or []
    return "\n".join((row.get("heading", "") + "\n" + row.get("text", "")) for row in sections if isinstance(row, dict))


def _score(base: float, text: str, positive: tuple[tuple[tuple[str, ...], float], ...], negative: tuple[tuple[tuple[str, ...], float], ...] = ()) -> float:
    value = base
    for terms, weight in positive:
        if _has_any(text, terms):
            value += weight
    for terms, weight in negative:
        if _has_any(text, terms):
            value -= weight
    return round(max(0.0, min(1.0, value)), 3)


def _sample_size_bonus(text: str) -> float:
    values = [int(match.group(1)) for match in re.finditer(r"\b(?:n\s*=\s*|cohort of\s+|samples?\s*[:=]?\s*)(\d{2,5})\b", text)]
    if not values:
        return 0.0
    largest = max(values)
    if largest >= 1000:
        return 0.16
    if largest >= 200:
        return 0.11
    if largest >= 50:
        return 0.07
    return 0.03


def assess_contribution(manuscript_summary: dict, profile: dict, manuscript_full: dict | None = None) -> dict:
    title = manuscript_summary.get("title") or ""
    abstract = manuscript_summary.get("abstract") or ""
    headings = " ".join(manuscript_summary.get("section_headings") or [])
    full = _section_text(manuscript_full)
    text = _norm(" ".join([title, abstract, headings, full]))

    novelty = _score(0.35, text, (
        (("novel", "new", "first", "previously unreported"), 0.10),
        (("rare disease", "mitochondrial disease", "inherited metabolic"), 0.08),
        (("dataset", "cohort", "whole-blood", "whole blood", "rna-seq", "rna sequencing"), 0.10),
        (("software", "application", "gui", "web server", "package"), 0.08),
        (("multi-cohort", "integrating", "integrated", "publicly available"), 0.06),
    ))
    evidence_strength = _score(0.30 + _sample_size_bonus(text), text, (
        (("external validation", "independent validation", "independent cohort", "held-out", "test set"), 0.16),
        (("cross-validation", "cross validation", "bootstrap"), 0.08),
        (("baseline", "benchmark", "compared with", "comparison"), 0.08),
        (("statistical", "confidence interval", "p-value", "fdr"), 0.06),
        (("prospective", "randomized", "clinical trial"), 0.12),
    ), (
        (("pilot", "preliminary", "small cohort", "limited sample"), 0.08),
    ))
    clinical_relevance = _score(0.28, text, (
        (("patient", "patients", "clinical cohort", "diagnosis", "diagnostic", "prognosis"), 0.18),
        (("mitochondrial disease", "rare disease", "inherited metabolic"), 0.12),
        (("whole blood", "whole-blood", "clinical sample", "blood"), 0.08),
        (("clinical utility", "decision support", "screening"), 0.10),
    ))
    method_strength = _score(0.30, text, (
        (("machine learning", "classifier", "classification", "neural network", "variational autoencoder", "vae"), 0.10),
        (("cross-validation", "held-out", "test set", "external validation"), 0.12),
        (("baseline", "benchmark", "ablation", "feature importance", "interpretability", "explainable"), 0.08),
        (("leakage", "batch effect", "confound", "normalization"), 0.06),
    ))
    resource_value = _score(0.25, text, (
        (("software", "application", "gui", "desktop application", "package", "workflow"), 0.18),
        (("dataset", "data availability", "publicly available", "repository", "github"), 0.14),
        (("rna-seq", "rna sequencing", "transcriptomics"), 0.06),
    ))
    readiness = _score(0.25, text, (
        (("abstract",), 0.08 if abstract else 0.0),
        (("methods", "materials and methods"), 0.08),
        (("discussion", "limitations"), 0.08),
        (("ethics", "institutional review", "irb", "informed consent"), 0.08),
        (("data availability", "code availability", "github", "repository"), 0.08),
    ))
    if (manuscript_summary.get("reference_count") or 0) >= 30:
        readiness = min(1.0, round(readiness + 0.06, 3))
    if (manuscript_summary.get("word_count") or 0) >= 4000:
        readiness = min(1.0, round(readiness + 0.05, 3))

    scores = {
        "novelty": novelty,
        "evidence_strength": evidence_strength,
        "clinical_relevance": clinical_relevance,
        "method_strength": method_strength,
        "resource_value": resource_value,
        "readiness": readiness,
    }
    composite = round(
        0.18 * novelty
        + 0.24 * evidence_strength
        + 0.18 * clinical_relevance
        + 0.16 * method_strength
        + 0.12 * resource_value
        + 0.12 * readiness,
        3,
    )
    if composite >= 0.86 and evidence_strength >= 0.82 and novelty >= 0.78:
        tier = "elite_general"
    elif composite >= 0.80 and evidence_strength >= 0.72 and novelty >= 0.70:
        tier = "high_impact_specialty"
    elif composite >= 0.58:
        tier = "strong_specialty"
    elif composite >= 0.42:
        tier = "solid_specialty"
    else:
        tier = "exploratory"

    strengths: list[str] = []
    limitations: list[str] = []
    if clinical_relevance >= 0.60:
        strengths.append("clinically relevant disease/cohort framing")
    if resource_value >= 0.55:
        strengths.append("reusable data/software/workflow component")
    if method_strength >= 0.55:
        strengths.append("computational method or model evidence is described")
    if evidence_strength < 0.55:
        limitations.append("validation strength is not clearly high from parsed text")
    if novelty < 0.55:
        limitations.append("novelty signal is moderate or unclear")
    if readiness < 0.55:
        limitations.append("submission-readiness signals such as data/code/ethics/limitations may need checking")

    band = {
        "exploratory": "safe_specialty",
        "solid_specialty": "specialty_target",
        "strong_specialty": "selective_specialty",
        "high_impact_specialty": "high_impact_specialty",
        "elite_general": "elite_general",
    }[tier]
    avoid = {
        "exploratory": ["high_impact_specialty", "top_clinical", "elite_general"],
        "solid_specialty": ["top_clinical", "elite_general"],
        "strong_specialty": ["elite_general"],
        "high_impact_specialty": [],
        "elite_general": [],
    }[tier]
    recommended = {
        "exploratory": ["safe_specialty", "broad_megajournal"],
        "solid_specialty": ["specialty_target", "safe_specialty", "selective_specialty"],
        "strong_specialty": ["selective_specialty", "specialty_target", "safe_specialty"],
        "high_impact_specialty": ["high_impact_specialty", "selective_specialty", "specialty_target"],
        "elite_general": ["elite_general", "top_clinical", "high_impact_specialty"],
    }[tier]
    return {
        "contribution_tier": tier,
        "ambition_band": band,
        "recommended_strategy": "safe" if tier == "exploratory" else "balanced",
        "composite_score": composite,
        "scores": scores,
        "strengths": strengths,
        "limitations": limitations,
        "avoid_bands": avoid,
        "recommended_bands": recommended,
        "evidence": {
            "title": title,
            "word_count": manuscript_summary.get("word_count"),
            "reference_count": manuscript_summary.get("reference_count"),
            "profile": profile,
        },
    }


def classify_venue_ambition(venue: VenueHit) -> str:
    name = _norm(venue.name)
    impact = venue.impact_proxy or 0.0
    if name in {"nature", "science", "cell"}:
        return "elite_general"
    if name in {"the lancet", "lancet", "new england journal of medicine", "bmj", "jama"}:
        return "top_clinical"
    if name.startswith("nature ") or name.startswith("cell "):
        return "high_impact_specialty"
    if name in {"genome biology", "nucleic acids research", "nature genetics", "science translational medicine"}:
        return "high_impact_specialty"
    if name in {"scientific reports", "international journal of molecular sciences", "plos one", "peerj"}:
        return "broad_megajournal"
    if impact >= 5.0:
        return "high_impact_specialty"
    if name in {"mitochondrion", "journal of inherited metabolic disease", "molecular genetics and metabolism"}:
        return "selective_specialty"
    if venue.specialty_confidence and venue.specialty_confidence >= 0.90:
        return "selective_specialty"
    if venue.specialty_confidence and venue.specialty_confidence >= 0.65:
        return "specialty_target"
    if _has_any(name, ("journal of", "bmc ", "frontiers in", "molecular", "genomics", "bioinformatics", "mitochondrion")):
        return "specialty_target"
    return "fallback"


def ambition_alignment(contribution: dict | None, venue_band: str) -> tuple[float, str, str]:
    if not contribution:
        return 0.0, "unknown", "no contribution assessment available"
    tier = contribution.get("contribution_tier") or "solid_specialty"
    manuscript_level = TIER_ORDER.get(tier, 1)
    venue_level = VENUE_AMBITION_ORDER.get(venue_band, 1)
    if venue_band in set(contribution.get("avoid_bands") or []):
        return -0.18, tier, f"venue ambition band {venue_band} exceeds contribution assessment"
    if venue_band in set(contribution.get("recommended_bands") or []):
        return 0.06, tier, f"venue ambition band {venue_band} matches contribution assessment"
    if venue_level >= manuscript_level + 2:
        return -0.12, tier, f"venue ambition band {venue_band} is probably too ambitious"
    if venue_level < max(0, manuscript_level - 2):
        return -0.04, tier, f"venue ambition band {venue_band} may be conservative for this contribution"
    return 0.0, tier, "venue ambition is acceptable"


def ambition_cap(contribution: dict | None, venue_band: str, score: float) -> float:
    if not contribution:
        return score
    tier = contribution.get("contribution_tier") or "solid_specialty"
    if venue_band in set(contribution.get("avoid_bands") or []):
        if venue_band in {"elite_general", "top_clinical"}:
            return min(score, 0.40)
        return min(score, 0.48)
    if tier == "exploratory" and venue_band in {"high_impact_specialty", "selective_specialty"}:
        return min(score, 0.46)
    return score
