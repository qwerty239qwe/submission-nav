from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx


OPENALEX_WORKS = "https://api.openalex.org/works"
OPENALEX_SOURCES = "https://api.openalex.org/sources"


DEFAULT_TARGETS = [
    {"paper": "plos_comp_biol", "journal": "PLOS Computational Biology", "query": "computational biology machine learning"},
    {"paper": "plos_one", "journal": "PLOS ONE", "query": "biology public health"},
    {"paper": "elife", "journal": "eLife", "query": "cell biology neuroscience"},
    {"paper": "scientific_reports", "journal": "Scientific Reports", "query": "materials science biology"},
    {"paper": "frontiers_immunology", "journal": "Frontiers in Immunology", "query": "immunology inflammation"},
    {"paper": "bmc_bioinformatics", "journal": "BMC Bioinformatics", "query": "bioinformatics algorithm"},
    {"paper": "peerj", "journal": "PeerJ", "query": "ecology genomics"},
    {"paper": "bmj_open", "journal": "BMJ Open", "query": "clinical epidemiology public health"},
]


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_").lower()


def _source_filter(source_id: str) -> str:
    short_id = source_id.rsplit("/", 1)[-1]
    return f"primary_location.source.id:{short_id},is_oa:true,has_fulltext:true,type:article"


def _pdf_url(work: dict) -> str | None:
    locations = [work.get("primary_location") or {}]
    locations.extend(work.get("locations") or [])
    for loc in locations:
        pdf_url = loc.get("pdf_url")
        if pdf_url:
            return pdf_url
    oa = work.get("open_access") or {}
    oa_url = oa.get("oa_url")
    if oa_url and _looks_like_pdf(oa_url):
        return oa_url
    return None


def _looks_like_pdf(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.path.casefold().endswith(".pdf") or "type=printable" in parsed.query.casefold()


def _expected_venue(work: dict, fallback: str) -> str:
    source = ((work.get("primary_location") or {}).get("source") or {})
    return source.get("display_name") or fallback


def _openalex_source_id(journal: str, mailto: str | None) -> str | None:
    params = {"search": journal, "per-page": 5, "filter": "type:journal"}
    if mailto:
        params["mailto"] = mailto
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        response = client.get(OPENALEX_SOURCES, params=params)
        response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    best = max(results, key=lambda row: 100 if (row.get("display_name") or "").casefold() == journal.casefold() else 0)
    return best.get("id")


def _openalex_works(journal: str, query: str, per_page: int, mailto: str | None) -> list[dict]:
    source_id = _openalex_source_id(journal, mailto)
    if not source_id:
        return []
    params = {
        "search": query,
        "filter": _source_filter(source_id),
        "per-page": per_page,
        "sort": "publication_date:desc",
    }
    if mailto:
        params["mailto"] = mailto
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        response = client.get(OPENALEX_WORKS, params=params)
        response.raise_for_status()
        return response.json().get("results") or []


def _download_pdf(url: str, path: Path) -> bool:
    headers = {"User-Agent": "submission-nav verification benchmark builder"}
    with httpx.Client(follow_redirects=True, timeout=60, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").casefold()
        body = response.content
    if b"%PDF" not in body[:2048] and "pdf" not in content_type:
        return False
    path.write_bytes(body)
    return True


def build_manifest(targets: list[dict], out_dir: Path, per_target: int, mailto: str | None) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    failures: list[dict] = []
    for target in targets:
        journal = target["journal"]
        paper_id = target.get("paper") or _safe_name(journal)
        works = _openalex_works(journal, target.get("query", journal), per_target, mailto)
        saved = False
        for work in works:
            url = _pdf_url(work)
            if not url:
                continue
            pdf_path = out_dir / f"{paper_id}.pdf"
            try:
                if not _download_pdf(url, pdf_path):
                    continue
            except httpx.HTTPError:
                continue
            manifest.append({
                "paper": paper_id,
                "pdf": str(pdf_path),
                "expected_venue": _expected_venue(work, journal),
                "aliases": [journal],
                "doi": work.get("doi"),
                "title": work.get("display_name"),
                "source_url": url,
                "venue_types": ["journal"],
                "strategy": target.get("strategy", "balanced"),
            })
            saved = True
            break
        if not saved:
            failures.append({"paper": paper_id, "journal": journal, "reason": "no downloadable PDF found"})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "failures.json").write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--targets-json", help="Optional target journal/query JSON list.")
    ap.add_argument("--per-target", type=int, default=20)
    ap.add_argument("--mailto", default=None)
    args = ap.parse_args()
    targets = DEFAULT_TARGETS
    if args.targets_json:
        targets = json.loads(Path(args.targets_json).read_text(encoding="utf-8"))
    manifest = build_manifest(targets, Path(args.out_dir), args.per_target, args.mailto)
    print(json.dumps({"papers": len(manifest), "manifest": str(Path(args.out_dir) / "manifest.json")}, indent=2))


if __name__ == "__main__":
    _main()
