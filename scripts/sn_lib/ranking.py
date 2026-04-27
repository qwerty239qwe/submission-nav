from __future__ import annotations
from dataclasses import dataclass, asdict
from rapidfuzz import fuzz
from .cli import emit_json
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
        fit = max(concept_fit, text_fit)
        imp = _impact(v.impact_proxy)
        scoped_imp = _impact_weight(imp, fit, text_fit)
        oa = _oa_bonus(v)
        pen = _apc_penalty(v.apc_usd, apc_budget_usd)
        broad_pen = _broad_scope_penalty(v, fit, text_fit, imp)
        raw_score = w_fit * fit + w_impact * scoped_imp + w_oa * oa - pen - broad_pen
        suitability = score_suitability(
            v,
            raw_score=raw_score,
            base_fit=fit,
            profile=profile,
            strategy=strategy,
            apc_budget_usd=apc_budget_usd,
            oa_preference=oa_preference,
        )
        score = suitability.strategy_score
        suitability_payload = suitability.to_dict()
        out.append(Ranked(v, round(score, 4), {
            "strategy": strategy,
            "fit": round(fit, 3),
            "concept_fit": round(concept_fit, 3),
            "text_fit": round(text_fit, 3),
            "impact": round(scoped_imp, 3),
            "oa_bonus": round(oa, 3),
            "apc_penalty": round(pen, 3),
            "broad_scope_penalty": round(broad_pen, 3),
            "raw_score": round(raw_score, 4),
            "suitability_score": suitability_payload["score"],
            "strategy_score": suitability_payload["strategy_score"],
            "scope_fit": suitability_payload["scope_fit"],
            "article_type_fit": suitability_payload["article_type_fit"],
            "cost_fit": suitability_payload["cost_fit"],
            "oa_fit": suitability_payload["oa_fit"],
            "risk_label": suitability_payload["risk_label"],
            "risk_reasons": suitability_payload["risk_reasons"],
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

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", nargs="+", required=True)
    ap.add_argument("--venues-json", required=True, help="path to JSON list from venues module")
    ap.add_argument("--apc-budget", type=float, default=None)
    ap.add_argument("--strategy", default="balanced", choices=["balanced", "ambitious", "safe", "fast", "low-cost", "oa-only", "broad"])
    ap.add_argument("--oa-preference", default="any", choices=["any", "oa-only", "avoid-oa"])
    ap.add_argument("--manuscript-summary-json", help="Optional parsed manuscript summary JSON for article-type suitability.")
    ap.add_argument("--out", help="Optional path to write JSON output.")
    ap.add_argument("--top-n", type=int, default=None, help="Optionally limit stdout/full output to the top N ranked venues.")
    ap.add_argument("--agent-out", help="Optional path to write a compact summary JSON for agent use.")
    ap.add_argument("--agent-top-n", type=int, default=12, help="Number of entries to keep in the compact agent summary.")
    ap.add_argument("--agent-concept-limit", type=int, default=5, help="Max concepts per venue in the compact agent summary.")
    ap.add_argument("--agent-min-score", type=float, default=None, help="Optional minimum score threshold for the compact agent summary.")
    args = ap.parse_args()
    raw = json.loads(open(args.venues_json, encoding="utf-8-sig").read())
    venues = [VenueHit(**r) for r in raw]
    summary = {}
    if args.manuscript_summary_json:
        summary = json.loads(open(args.manuscript_summary_json, encoding="utf-8-sig").read())
    ranked = rank_venues(
        args.concepts,
        venues,
        apc_budget_usd=args.apc_budget,
        strategy=args.strategy,
        oa_preference=args.oa_preference,
        ms_title=summary.get("title"),
        ms_abstract=summary.get("abstract"),
    )
    full = ranked[:args.top_n] if args.top_n is not None else ranked
    emit_json([r.to_dict() for r in full], args.out)
    if args.agent_out:
        emit_json(
            summarize_ranked(
                ranked,
                top_n=args.agent_top_n,
                concept_limit=args.agent_concept_limit,
                min_score=args.agent_min_score,
            ),
            args.agent_out,
        )

if __name__ == "__main__":
    _main()
