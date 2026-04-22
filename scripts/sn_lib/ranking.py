from __future__ import annotations
from dataclasses import dataclass, asdict
from rapidfuzz import fuzz
from .cli import emit_json
from .venues import VenueHit

@dataclass
class Ranked:
    venue: VenueHit
    score: float
    rationale: dict

    def to_dict(self) -> dict:
        return {"venue": self.venue.to_dict(), "score": self.score, "rationale": self.rationale}

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
    tokens = [field for field in text_fields if field]
    return _fit(ms_concepts, tokens)

def _impact(impact_proxy: float | None) -> float:
    if impact_proxy is None:
        return 0.0
    import math
    return min(1.0, math.log1p(max(0.0, impact_proxy)) / math.log1p(20))

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
    w_fit: float = 0.6,
    w_impact: float = 0.3,
    w_oa: float = 0.1,
) -> list[Ranked]:
    out: list[Ranked] = []
    for v in venues:
        concept_fit = _fit(ms_concepts, v.concepts)
        text_fit = _text_fit(ms_concepts, v)
        fit = max(concept_fit, text_fit)
        imp = _impact(v.impact_proxy)
        oa = _oa_bonus(v)
        pen = _apc_penalty(v.apc_usd, apc_budget_usd)
        score = w_fit * fit + w_impact * imp + w_oa * oa - pen
        out.append(Ranked(v, round(score, 4), {
            "fit": round(fit, 3),
            "concept_fit": round(concept_fit, 3),
            "text_fit": round(text_fit, 3),
            "impact": round(imp, 3),
            "oa_bonus": round(oa, 3),
            "apc_penalty": round(pen, 3),
        }))
    out.sort(key=lambda r: r.score, reverse=True)
    return out

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", nargs="+", required=True)
    ap.add_argument("--venues-json", required=True, help="path to JSON list from venues module")
    ap.add_argument("--apc-budget", type=float, default=None)
    ap.add_argument("--out", help="Optional path to write JSON output.")
    args = ap.parse_args()
    raw = json.loads(open(args.venues_json, encoding="utf-8-sig").read())
    venues = [VenueHit(**r) for r in raw]
    ranked = rank_venues(args.concepts, venues, apc_budget_usd=args.apc_budget)
    emit_json([r.to_dict() for r in ranked], args.out)

if __name__ == "__main__":
    _main()
