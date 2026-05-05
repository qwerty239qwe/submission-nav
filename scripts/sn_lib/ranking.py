from __future__ import annotations
from dataclasses import dataclass, asdict
from rapidfuzz import fuzz
from .cli import emit_json
from .contribution import ambition_alignment, ambition_cap, classify_venue_ambition
from .domain_gate import apply_domain_gate, assess_domain_compatibility
from .suitability import infer_manuscript_profile, score_suitability
from .venues import VenueHit

@dataclass
class Ranked:
    venue: VenueHit
    score: float
    rationale: dict

    def to_dict(self) -> dict:
        return {"venue": self.venue.to_dict(), "score": self.score, "rationale": self.rationale}

    def to_summary_dict(self, concept_limit: int = 5) -> dict:
        concepts = self.venue.concepts[:concept_limit]
        return {
            "journal": self.venue.name,
            "publisher": self.venue.publisher,
            "fit": self.rationale["fit"],
            "impact_proxy": self.venue.impact_proxy,
            "is_oa": self.venue.is_oa,
            "apc_usd": self.venue.apc_usd,
            "h_index": self.venue.h_index,
            "evidence_count": getattr(self.venue, "evidence_count", None),
            "source": self.venue.source,
            "top_concepts": concepts,
            "score": self.score,
            "raw_score": self.rationale.get("raw_score", self.score),
            "strategy_score": self.rationale.get("strategy_score", self.score),
            "suitability_score": self.rationale.get("suitability_score"),
            "risk_label": self.rationale.get("risk_label"),
            "risk_reasons": self.rationale.get("risk_reasons", []),
            "article_type_fit": self.rationale.get("article_type_fit"),
            "publisher_risk_label": self.rationale.get("publisher_risk_label"),
            "publisher_risk_reasons": self.rationale.get("publisher_risk_reasons", []),
            "specialty_domain": self.rationale.get("specialty_domain"),
            "specialty_fit": self.rationale.get("specialty_fit"),
            "venue_ambition_band": self.rationale.get("venue_ambition_band"),
            "contribution_tier": self.rationale.get("contribution_tier"),
            "ambition_reason": self.rationale.get("ambition_reason"),
            "domain_gate": self.rationale.get("domain_gate"),
            "domain_gate_reasons": self.rationale.get("domain_gate_reasons", []),
            "rationale": self.rationale,
        }

def _fit(ms_concepts: list[str], v_concepts: list[str]) -> float:
    if not ms_concepts or not v_concepts:
        return 0.0
    scores = []
    for mc in ms_concepts:
        best = max((fuzz.token_set_ratio(mc, vc) for vc in v_concepts), default=0)
        scores.append(best / 100.0)
    return sum(scores) / len(scores)


def _text_fit(ms_concepts: list[str], venue: VenueHit) -> float:
    text_fields = [venue.name]
    if venue.publisher:
        text_fields.append(venue.publisher)
    if venue.dblp_acronym:
        text_fields.append(venue.dblp_acronym)
    if venue.dblp_type:
        text_fields.append(venue.dblp_type)
    tokens = [field for field in text_fields if field]
    return _fit(ms_concepts, tokens)

def _impact(impact_proxy: float | None) -> float:
    if impact_proxy is None:
        return 0.0
    import math
    return min(1.0, math.log1p(max(0.0, impact_proxy)) / math.log1p(20))


def _impact_weight(imp: float, fit: float, text_fit: float) -> float:
    scope_signal = max(fit, text_fit)
    return imp * (0.25 + 0.75 * scope_signal)


def _broad_scope_penalty(venue: VenueHit, fit: float, text_fit: float, imp: float) -> float:
    name = (venue.name or "").lower()
    broad_tokens = ("nature", "science", "cell", "lancet", "review")
    if not any(token in name for token in broad_tokens):
        return 0.0
    if fit >= 0.55 or text_fit >= 0.45:
        return 0.0
    return round(max(0.0, imp - max(fit, text_fit)) * 0.12, 3)

def _oa_bonus(v: VenueHit) -> float:
    return 0.1 if v.is_oa else 0.0

def _apc_penalty(apc: float | None, budget: float | None) -> float:
    if budget is None or apc is None:
        return 0.0
    if apc <= budget:
        return 0.0
    return min(0.5, (apc - budget) / max(budget, 1.0) * 0.25)

def rank_venues(
    ms_concepts: list[str],
    venues: list[VenueHit],
    apc_budget_usd: float | None = None,
    strategy: str = "balanced",
    oa_preference: str = "any",
    ms_title: str | None = None,
    ms_abstract: str | None = None,
    contribution_assessment: dict | None = None,
    w_fit: float = 0.6,
    w_impact: float = 0.3,
    w_oa: float = 0.1,
) -> list[Ranked]:
    out: list[Ranked] = []
    profile = infer_manuscript_profile(
        ms_concepts,
        title=ms_title,
        abstract=ms_abstract,
        oa_preference=oa_preference,
    )
    for v in venues:
        concept_fit = _fit(ms_concepts, v.concepts)
        text_fit = _text_fit(ms_concepts, v)
        specialty_fit = min(1.0, max(0.0, v.specialty_confidence or 0.0))
        fit = max(concept_fit, text_fit, specialty_fit * 0.68)
        imp = _impact(v.impact_proxy)
        scoped_imp = _impact_weight(imp, fit, text_fit)
        oa = _oa_bonus(v)
        pen = _apc_penalty(v.apc_usd, apc_budget_usd)
        broad_pen = _broad_scope_penalty(v, fit, text_fit, imp)
        specialty_bonus = 0.08 * specialty_fit
        raw_score = w_fit * fit + w_impact * scoped_imp + w_oa * oa + specialty_bonus - pen - broad_pen
        suitability = score_suitability(
            v,
            raw_score=raw_score,
            base_fit=fit,
            profile=profile,
            strategy=strategy,
            apc_budget_usd=apc_budget_usd,
            oa_preference=oa_preference,
        )
        venue_band = classify_venue_ambition(v)
        ambition_delta, contribution_tier, ambition_reason = ambition_alignment(contribution_assessment, venue_band)
        uncapped_score = ambition_cap(contribution_assessment, venue_band, suitability.strategy_score + ambition_delta)
        domain_gate = assess_domain_compatibility(ms_concepts, ms_title, ms_abstract, profile, v)
        score = apply_domain_gate(uncapped_score, domain_gate)
        suitability_payload = suitability.to_dict()
        domain_gate_payload = domain_gate.to_dict()
        out.append(Ranked(v, round(score, 4), {
            "strategy": strategy,
            "fit": round(fit, 3),
            "concept_fit": round(concept_fit, 3),
            "text_fit": round(text_fit, 3),
            "specialty_fit": round(specialty_fit, 3),
            "specialty_domain": v.specialty_domain,
            "specialty_bonus": round(specialty_bonus, 3),
            "impact": round(scoped_imp, 3),
            "oa_bonus": round(oa, 3),
            "apc_penalty": round(pen, 3),
            "broad_scope_penalty": round(broad_pen, 3),
            "raw_score": round(raw_score, 4),
            "suitability_score": suitability_payload["score"],
            "strategy_score": suitability_payload["strategy_score"],
            "pre_domain_gate_score": round(uncapped_score, 4),
            "scope_fit": suitability_payload["scope_fit"],
            "article_type_fit": suitability_payload["article_type_fit"],
            "cost_fit": suitability_payload["cost_fit"],
            "oa_fit": suitability_payload["oa_fit"],
            "publisher_integrity_fit": suitability_payload["publisher_integrity_fit"],
            "publisher_risk_label": suitability_payload["publisher_risk_label"],
            "publisher_risk_reasons": suitability_payload["publisher_risk_reasons"],
            "risk_label": suitability_payload["risk_label"],
            "risk_reasons": suitability_payload["risk_reasons"],
            "venue_ambition_band": venue_band,
            "contribution_tier": contribution_tier,
            "ambition_delta": round(ambition_delta, 3),
            "ambition_reason": ambition_reason,
            "domain_gate": domain_gate_payload["label"],
            "domain_gate_score_cap": domain_gate_payload["score_cap"],
            "domain_gate_penalty": domain_gate_payload["penalty"],
            "domain_gate_reasons": domain_gate_payload["reasons"],
            "manuscript_domains": domain_gate_payload["manuscript_domains"],
            "venue_domains": domain_gate_payload["venue_domains"],
            "method_domains": domain_gate_payload["method_domains"],
            "manuscript_profile": suitability_payload["profile"],
        }))
    out.sort(key=lambda r: r.score, reverse=True)
    return out


def summarize_ranked(
    ranked: list[Ranked],
    top_n: int | None = None,
    concept_limit: int = 5,
    min_score: float | None = None,
) -> list[dict]:
    items = ranked
    if min_score is not None:
        items = [r for r in items if r.score >= min_score]
    if top_n is not None:
        items = items[:top_n]
    return [r.to_summary_dict(concept_limit=concept_limit) for r in items]


def _bucket_for(item: Ranked) -> tuple[str, str]:
    rationale = item.rationale
    risk = rationale.get("risk_label")
    reasons = rationale.get("risk_reasons") or []
    article_type_fit = rationale.get("article_type_fit") or 1.0
    publisher_label = rationale.get("publisher_risk_label")
    venue_band = rationale.get("venue_ambition_band")
    ambition_reason = rationale.get("ambition_reason") or ""
    domain_gate = rationale.get("domain_gate")
    impact = _impact(item.venue.impact_proxy)
    if publisher_label in {"potential_predatory_match", "hijacked_or_identity_risk"}:
        return "avoid", "publisher integrity risk"
    if article_type_fit <= 0.1:
        return "avoid", "article type mismatch"
    if risk == "high":
        return "avoid", "high risk"
    if article_type_fit < 0.7 or any("outside the manuscript" in reason for reason in reasons):
        return "fallback", "scope or article-type caution"
    if domain_gate in {"conflict", "method_only_match"}:
        return "fallback", "domain-community caution"
    if domain_gate == "adjacent" and item.score < 0.50:
        return "fallback", "adjacent-domain low-confidence venue"
    if venue_band == "broad_megajournal":
        return "fallback", "broad fallback venue"
    if "exceeds contribution assessment" in ambition_reason and venue_band in {"elite_general", "top_clinical"}:
        return "avoid", "ambition mismatch"
    if "exceeds contribution assessment" in ambition_reason or "probably too ambitious" in ambition_reason:
        return "fallback", "ambition caution"
    if item.score >= 0.43 and impact >= 0.30:
        return "stretch", "higher-impact plausible venue"
    if item.score >= 0.50:
        return "target", "best balance of fit and suitability"
    if item.score >= 0.40:
        return "safe", "plausible lower-risk fallback"
    return "fallback", "low confidence or weak score"


def summarize_bucketed(
    ranked: list[Ranked],
    strategy: str = "balanced",
    top_n: int = 12,
    per_bucket: int = 5,
    concept_limit: int = 5,
) -> dict:
    bucket_order = {
        "ambitious": ["stretch", "target", "safe", "fallback", "avoid"],
        "safe": ["target", "safe", "fallback", "stretch", "avoid"],
        "fast": ["safe", "target", "fallback", "stretch", "avoid"],
        "low-cost": ["target", "safe", "fallback", "stretch", "avoid"],
        "oa-only": ["target", "safe", "fallback", "stretch", "avoid"],
        "broad": ["stretch", "target", "safe", "fallback", "avoid"],
        "balanced": ["target", "stretch", "safe", "fallback", "avoid"],
    }.get(strategy, ["target", "stretch", "safe", "fallback", "avoid"])
    buckets: dict[str, list[dict]] = {name: [] for name in ["stretch", "target", "safe", "fallback", "avoid"]}
    counts: dict[str, int] = {name: 0 for name in buckets}
    for item in ranked:
        bucket, reason = _bucket_for(item)
        counts[bucket] += 1
        row = item.to_summary_dict(concept_limit=concept_limit)
        row["bucket"] = bucket
        row["bucket_reason"] = reason
        if len(buckets[bucket]) < per_bucket:
            buckets[bucket].append(row)
    ordered_top: list[dict] = []
    for bucket in bucket_order:
        for row in buckets[bucket]:
            if len(ordered_top) >= top_n:
                break
            ordered_top.append(row)
        if len(ordered_top) >= top_n:
            break
    return {
        "strategy": strategy,
        "bucket_order": bucket_order,
        "top": ordered_top,
        "buckets": buckets,
        "counts": counts,
    }
