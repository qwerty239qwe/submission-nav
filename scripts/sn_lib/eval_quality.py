from __future__ import annotations


MEGAJOURNALS = {
    "plos one",
    "scientific reports",
    "international journal of molecular sciences",
    "heliyon",
    "peerj",
}


def _norm(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("&", "and").split())


def item_quality_flags(item: dict) -> dict:
    reasons = " | ".join(item.get("risk_reasons") or []).casefold()
    journal = _norm(item.get("journal"))
    article_type_fit = item.get("article_type_fit")
    scope_fit = item.get("rationale", {}).get("scope_fit", item.get("scope_fit"))
    bucket = item.get("bucket")
    venue_band = item.get("venue_ambition_band")
    return {
        "article_type_mismatch": (
            (article_type_fit is not None and article_type_fit < 0.7)
            or any(term in reasons for term in ("review-only", "methods/protocol", "data/resource"))
        ),
        "high_risk": item.get("risk_label") == "high" or bucket == "avoid",
        "scope_caution": (
            (scope_fit is not None and scope_fit < 0.4)
            or "outside the manuscript" in reasons
            or "weak scope evidence" in reasons
        ),
        "broad_megajournal": venue_band == "broad_megajournal" or journal in MEGAJOURNALS,
    }


def summarize_rank_quality(items: list[dict], top_n: int = 5) -> dict:
    subset = items[:top_n]
    counts = {
        "article_type_mismatch": 0,
        "high_risk": 0,
        "scope_caution": 0,
        "broad_megajournal": 0,
    }
    for item in subset:
        flags = item_quality_flags(item)
        for key in counts:
            counts[key] += int(flags[key])
    denominator = max(len(subset), 1)
    return {
        "top_n": top_n,
        "evaluated": len(subset),
        "counts": counts,
        "rates": {key: round(value / denominator, 3) for key, value in counts.items()},
        "has_contamination": any(value > 0 for value in counts.values()),
    }
