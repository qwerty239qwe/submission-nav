from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from sn_lib.concepts import derive_from_summary
from sn_lib.parse import parse_manuscript
from sn_lib.ranking import rank_venues
from sn_lib.venues import search_venues


def _load_manifest(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _normalize_name(name: str | None) -> str:
    return " ".join((name or "").casefold().replace("&", "and").split())


def _expected_names(row: dict) -> list[str]:
    names = [row.get("journal") or row.get("venue") or row.get("expected_venue")]
    names.extend(row.get("aliases") or [])
    return [_normalize_name(name) for name in names if name]


def _rank_of_expected(items, expected_names: list[str]) -> int | None:
    expected = set(expected_names)
    for idx, item in enumerate(items, start=1):
        venue = item.venue if hasattr(item, "venue") else item
        names = [
            getattr(venue, "name", None),
            getattr(venue, "dblp_acronym", None),
        ]
        if any(_normalize_name(name) in expected for name in names if name):
            return idx
    return None


def _hit_at(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def _metrics(results: list[dict]) -> dict:
    n = len(results)
    if n == 0:
        return {
            "papers": 0,
            "retrieval_recall": 0.0,
            "ranked_recall": 0.0,
            "hit_at_1": 0.0,
            "hit_at_3": 0.0,
            "hit_at_5": 0.0,
            "hit_at_10": 0.0,
            "mrr": 0.0,
            "median_rank": None,
        }
    ranks = [row["published_rank"] for row in results if row["published_rank"] is not None]
    reciprocal_ranks = [(1 / row["published_rank"]) if row["published_rank"] else 0.0 for row in results]
    return {
        "papers": n,
        "retrieval_recall": round(sum(row["retrieved"] for row in results) / n, 3),
        "ranked_recall": round(sum(row["published_rank"] is not None for row in results) / n, 3),
        "hit_at_1": round(sum(_hit_at(row["published_rank"], 1) for row in results) / n, 3),
        "hit_at_3": round(sum(_hit_at(row["published_rank"], 3) for row in results) / n, 3),
        "hit_at_5": round(sum(_hit_at(row["published_rank"], 5) for row in results) / n, 3),
        "hit_at_10": round(sum(_hit_at(row["published_rank"], 10) for row in results) / n, 3),
        "mrr": round(sum(reciprocal_ranks) / n, 3),
        "median_rank": statistics.median(ranks) if ranks else None,
    }


def _markdown_report(summary: dict) -> str:
    metrics = summary["metrics"]
    lines = [
        "# submission-strategist verification report",
        "",
        "## Metrics",
        "",
        f"- papers: `{metrics['papers']}`",
        f"- retrieval recall: `{metrics['retrieval_recall']}`",
        f"- ranked recall: `{metrics['ranked_recall']}`",
        f"- hit@1: `{metrics['hit_at_1']}`",
        f"- hit@3: `{metrics['hit_at_3']}`",
        f"- hit@5: `{metrics['hit_at_5']}`",
        f"- hit@10: `{metrics['hit_at_10']}`",
        f"- MRR: `{metrics['mrr']}`",
        f"- median rank: `{metrics['median_rank']}`",
        "",
        "## Cases",
        "",
        "| Paper | Expected venue | Retrieved | Rank | Top 1 | Concepts |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in summary["results"]:
        concepts = ", ".join(row["concepts"][:3])
        rank = row["published_rank"] if row["published_rank"] is not None else "not found"
        lines.append(
            f"| {row['paper']} | {row['expected_venue']} | {row['retrieved']} | {rank} | {row['top1'] or ''} | {concepts} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Retrieval recall measures whether the expected venue was found anywhere before ranking.",
        "- Hit@k and MRR measure whether ranking places the expected venue near the top.",
        "- A good shortlist generator should first improve retrieval recall; a good recommender should improve hit@3/hit@5 and MRR.",
    ])
    return "\n".join(lines) + "\n"


def evaluate(manifest_path: Path, out_dir: Path, per_page: int = 40, default_venue_types: tuple[str, ...] = ("journal",)) -> dict:
    manifest = _load_manifest(manifest_path)
    _ensure_dir(out_dir)
    results: list[dict] = []

    for row in manifest:
        pdf_path = Path(row["pdf"])
        venue_types = tuple(row.get("venue_types") or default_venue_types)
        expected_names = _expected_names(row)
        expected_display = row.get("journal") or row.get("venue") or row.get("expected_venue")
        manuscript = parse_manuscript(pdf_path)
        summary = manuscript.to_summary_dict()
        concepts_payload = derive_from_summary(summary)
        concepts = concepts_payload["concepts"]
        queries = concepts_payload["queries"] or concepts[:1]

        merged_hits = []
        seen = set()
        for query in queries:
            for hit in search_venues(query, per_page=per_page, venue_types=venue_types):
                key = hit.id or hit.issn or hit.name
                if key in seen:
                    continue
                seen.add(key)
                merged_hits.append(hit)

        ranked = rank_venues(
            concepts,
            merged_hits,
            strategy=row.get("strategy", "balanced"),
            oa_preference=row.get("oa_preference", "any"),
            ms_title=summary.get("title"),
            ms_abstract=summary.get("abstract"),
        )
        retrieval_rank = _rank_of_expected(merged_hits, expected_names)
        published_rank = _rank_of_expected(ranked, expected_names)

        payload = {
            "paper": row["paper"],
            "pdf": str(pdf_path),
            "expected_venue": expected_display,
            "venue_types": list(venue_types),
            "title": summary["title"],
            "concepts": concepts,
            "queries": queries,
            "retrieved": retrieval_rank is not None,
            "retrieval_rank": retrieval_rank,
            "top1": ranked[0].venue.name if ranked else None,
            "published_rank": published_rank,
            "top10_contains_published": published_rank is not None and published_rank <= 10,
            "top10": [item.venue.name for item in ranked[:10]],
        }
        results.append(payload)
        (out_dir / f'{row["paper"]}_eval.json').write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    summary = {
        "manifest": str(manifest_path),
        "per_page": per_page,
        "default_venue_types": list(default_venue_types),
        "metrics": _metrics(results),
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown_report(summary), encoding="utf-8")
    return summary


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="Path to JSON manifest with paper/pdf/journal entries.")
    ap.add_argument("--out-dir", required=True, help="Directory to write evaluation outputs.")
    ap.add_argument("--per-page", type=int, default=40)
    ap.add_argument("--venue-types", nargs="+", default=["journal"], help="Default venue types for entries without their own venue_types field.")
    args = ap.parse_args()
    summary = evaluate(Path(args.manifest), Path(args.out_dir), per_page=args.per_page, default_venue_types=tuple(args.venue_types))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
