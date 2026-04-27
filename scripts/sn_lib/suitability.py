from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from .venues import VenueHit


STRATEGIES = {"balanced", "ambitious", "safe", "fast", "low-cost", "oa-only", "broad"}


@dataclass(frozen=True)
class ManuscriptProfile:
    contribution_type: str
    domains: tuple[str, ...]
    urgency: str = "normal"
    oa_preference: str = "any"

    def to_dict(self) -> dict:
        return {
            "contribution_type": self.contribution_type,
            "domains": list(self.domains),
            "urgency": self.urgency,
            "oa_preference": self.oa_preference,
        }


@dataclass(frozen=True)
class Suitability:
    score: float
    strategy_score: float
    scope_fit: float
    article_type_fit: float
    cost_fit: float
    oa_fit: float
    risk_label: str
    risk_reasons: tuple[str, ...]
    profile: ManuscriptProfile

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "strategy_score": round(self.strategy_score, 4),
            "scope_fit": round(self.scope_fit, 3),
            "article_type_fit": round(self.article_type_fit, 3),
            "cost_fit": round(self.cost_fit, 3),
            "oa_fit": round(self.oa_fit, 3),
            "risk_label": self.risk_label,
            "risk_reasons": list(self.risk_reasons),
            "profile": self.profile.to_dict(),
        }


def _norm(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def infer_manuscript_profile(
    concepts: list[str],
    title: str | None = None,
    abstract: str | None = None,
    oa_preference: str = "any",
) -> ManuscriptProfile:
    title_text = _norm(title)
    abstract_text = _norm(abstract)
    text = _norm(" ".join([title or "", abstract or "", " ".join(concepts)]))

    contribution_type = "original_research"
    if _has_any(text, ("systematic review", "scoping review", "narrative review", "review article", "meta-analysis")):
        contribution_type = "review"
    elif _has_any(text, ("database", "dataset", "data resource", "knowledgebase", "benchmark dataset")):
        contribution_type = "dataset"
    elif _has_any(text, ("software package", "web server", "toolkit", "open-source software", "workflow tool", "pipeline tool")):
        contribution_type = "software"
    elif _has_any(title_text, ("novel method", "new method", "methodological", "algorithm", "framework", "protocol")):
        contribution_type = "method_development"
    elif re.search(r"\b(we|this study)\s+(present|propose|introduce|develop)\s+(a|an|the)?\s*(new|novel)?\s*(method|algorithm|framework|protocol|model)\b", abstract_text):
        contribution_type = "method_development"
    elif _has_any(text, ("clinical trial", "patients", "patient cohort", "randomized", "diagnosis", "prognosis")):
        contribution_type = "clinical"

    domain_terms = {
        "toxicology": ("toxicity", "toxicology", "toxicological", "toxicant", "admet"),
        "cheminformatics": ("cheminformatics", "molecular fingerprint", "qsar", "chemical space", "molecular descriptor"),
        "pharmacology": ("drug discovery", "drug development", "pharmacology", "drug safety"),
        "bioinformatics": ("bioinformatics", "computational biology", "omics", "genomics"),
        "machine_learning": ("machine learning", "deep learning", "predictive model", "prediction", "classifier"),
        "clinical": ("clinical trial", "patient", "patients", "randomized", "diagnosis", "prognosis"),
    }
    domains = tuple(name for name, terms in domain_terms.items() if _has_any(text, terms))
    return ManuscriptProfile(
        contribution_type=contribution_type,
        domains=domains or ("general",),
        oa_preference=oa_preference,
    )


def _domain_scope_fit(profile: ManuscriptProfile, venue: VenueHit, base_fit: float) -> float:
    name = _norm(venue.name)
    concepts = _norm(" ".join(venue.concepts))
    text = f"{name} {concepts}"
    if "toxicology" in profile.domains:
        if name == "computational toxicology":
            return 0.95
        if _has_any(name, ("toxicology", "toxicological", "toxicity")):
            return max(base_fit, 0.88)
    if "cheminformatics" in profile.domains and _has_any(name, ("cheminformatics", "chemical information", "chemical information and modeling", "molecular informatics")):
        return max(base_fit, 0.88)
    boosts = {
        "toxicology": ("toxicology", "toxicological", "toxicity", "environmental health"),
        "cheminformatics": ("cheminformatics", "molecular informatics", "chemical information", "qsar"),
        "pharmacology": ("pharmacology", "drug discovery", "drug safety", "admet"),
        "bioinformatics": ("bioinformatics", "computational biology", "nucleic acids"),
        "machine_learning": ("machine learning", "artificial intelligence", "deep learning"),
        "clinical": ("clinical", "medicine", "translational"),
    }
    score = base_fit
    for domain in profile.domains:
        terms = boosts.get(domain, ())
        if terms and _has_any(text, terms):
            score = max(score, 0.78 if domain in {"toxicology", "cheminformatics"} else 0.62)
    return min(1.0, score)


def _venue_kind(venue: VenueHit) -> set[str]:
    name = _norm(venue.name)
    kinds: set[str] = set()
    if re.search(r"\b(nature reviews|annual reviews?|trends in|current opinion)\b", name):
        kinds.add("review")
    if re.search(r"\b(methods?|protocols?)\b", name):
        kinds.add("methods")
    if re.search(r"\b(scientific data|data in brief|database|data)\b", name):
        kinds.add("data")
    if name in {"science", "nature", "cell", "the lancet", "lancet", "new england journal of medicine"}:
        kinds.add("elite_broad")
    if name.startswith(("nature ", "cell ")):
        kinds.add("elite_family")
    if name in {"nature medicine", "the lancet", "lancet", "new england journal of medicine"}:
        kinds.add("clinical_elite")
    return kinds


def _article_type_fit(profile: ManuscriptProfile, venue: VenueHit) -> tuple[float, list[str]]:
    kinds = _venue_kind(venue)
    reasons: list[str] = []
    fit = 1.0
    ctype = profile.contribution_type

    if "review" in kinds and ctype != "review":
        fit = min(fit, 0.15)
        reasons.append("review-focused venue for a non-review manuscript")
    if "methods" in kinds and ctype not in {"method_development", "software"}:
        fit = min(fit, 0.45)
        reasons.append("methods/protocol venue but manuscript is not primarily a novel method")
    if "data" in kinds and ctype not in {"dataset", "software"}:
        fit = min(fit, 0.45)
        reasons.append("data/resource venue but manuscript is not primarily a dataset resource")
    if "elite_broad" in kinds:
        fit = min(fit, 0.25)
        reasons.append("very broad elite venue has high desk-reject risk")
    if "clinical_elite" in kinds and ctype != "clinical":
        fit = min(fit, 0.30)
        reasons.append("clinical elite venue but manuscript is not a clinical study")
    if "elite_family" in kinds and ctype == "original_research":
        fit = min(fit, 0.55)
        reasons.append("selective Nature/Cell-family venue needs unusually strong novelty")
    return fit, reasons


def _cost_fit(venue: VenueHit, apc_budget_usd: float | None) -> tuple[float, list[str]]:
    if apc_budget_usd is None or venue.apc_usd is None:
        return 0.75, []
    if venue.apc_usd <= apc_budget_usd:
        return 1.0, []
    over = venue.apc_usd - apc_budget_usd
    fit = max(0.0, 1.0 - over / max(apc_budget_usd, 1.0))
    return fit, [f"APC exceeds budget by about ${over:,.0f}"]


def _oa_fit(venue: VenueHit, oa_preference: str) -> tuple[float, list[str]]:
    pref = (oa_preference or "any").casefold()
    if pref in {"any", "no-preference"}:
        return 0.75 if venue.is_oa is None else 0.85, []
    if pref in {"oa", "oa-only", "open-access"}:
        if venue.is_oa is True:
            return 1.0, []
        return 0.0, ["open-access-only preference but venue is not marked OA"]
    if pref in {"avoid-oa", "non-oa"}:
        if venue.is_oa is True:
            return 0.25, ["author prefers to avoid OA venues"]
        return 1.0, []
    return 0.75, []


def _risk_label(reasons: list[str], article_type_fit: float, strategy_score: float) -> str:
    if article_type_fit <= 0.35 or len(reasons) >= 2:
        return "high"
    if strategy_score < 0.45 or article_type_fit < 0.7 or reasons:
        return "medium"
    return "low"


def _strategy_mix(
    strategy: str,
    raw_score: float,
    suitability_score: float,
    scope_fit: float,
    cost_fit: float,
    oa_fit: float,
    venue: VenueHit,
    article_type_fit: float,
) -> float:
    strategy = strategy if strategy in STRATEGIES else "balanced"
    impact = min(1.0, (venue.impact_proxy or 0.0) / 10.0)
    if strategy == "ambitious":
        return 0.42 * raw_score + 0.34 * suitability_score + 0.24 * impact - 0.08 * (1.0 - article_type_fit)
    if strategy == "safe":
        return 0.25 * raw_score + 0.70 * suitability_score + 0.05 * impact - 0.18 * (1.0 - article_type_fit)
    if strategy == "fast":
        return 0.30 * raw_score + 0.50 * suitability_score + 0.10 * oa_fit + 0.10 * cost_fit
    if strategy == "low-cost":
        return 0.25 * raw_score + 0.45 * suitability_score + 0.30 * cost_fit
    if strategy == "oa-only":
        return 0.25 * raw_score + 0.45 * suitability_score + 0.30 * oa_fit
    if strategy == "broad":
        return 0.50 * raw_score + 0.25 * suitability_score + 0.25 * max(scope_fit, impact)
    return 0.35 * raw_score + 0.55 * suitability_score + 0.10 * impact


def score_suitability(
    venue: VenueHit,
    raw_score: float,
    base_fit: float,
    profile: ManuscriptProfile,
    strategy: str = "balanced",
    apc_budget_usd: float | None = None,
    oa_preference: str = "any",
) -> Suitability:
    scope_fit = _domain_scope_fit(profile, venue, base_fit)
    article_type_fit, reasons = _article_type_fit(profile, venue)
    cost_fit, cost_reasons = _cost_fit(venue, apc_budget_usd)
    oa_fit, oa_reasons = _oa_fit(venue, oa_preference or profile.oa_preference)
    reasons.extend(cost_reasons)
    reasons.extend(oa_reasons)

    suitability_score = (
        0.50 * scope_fit
        + 0.30 * article_type_fit
        + 0.10 * cost_fit
        + 0.10 * oa_fit
    )
    strategy_score = _strategy_mix(
        strategy,
        raw_score,
        suitability_score,
        scope_fit,
        cost_fit,
        oa_fit,
        venue,
        article_type_fit,
    )
    return Suitability(
        score=max(0.0, min(1.0, suitability_score)),
        strategy_score=max(0.0, min(1.0, strategy_score)),
        scope_fit=scope_fit,
        article_type_fit=article_type_fit,
        cost_fit=cost_fit,
        oa_fit=oa_fit,
        risk_label=_risk_label(reasons, article_type_fit, strategy_score),
        risk_reasons=tuple(reasons),
        profile=profile,
    )
