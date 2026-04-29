from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Config, _canonical_key, _masked, _write_dotenv_value
from .runs import (
    clean_runs,
    list_runs,
    outputs_fresh,
    paths_for,
    query_filename,
    run_lock,
    slug,
    strategy_suffix,
    update_manifest,
    write_json_atomic,
)


EXIT_USER = 1
EXIT_INPUT = 2
EXIT_EXTERNAL = 3
EXIT_INTERNAL = 4


def _print_home(args) -> int:
    print(Path(__file__).resolve().parents[2])
    return 0


def emit_json(payload, out_path: str | None = None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        return
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def _print_ok(verb: str, output: Path | str) -> None:
    print(f"OK {verb} {output}")


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, payload: object) -> Path:
    write_json_atomic(path, payload)
    return path


def _cmd_parse(args) -> int:
    from .parse import parse_manuscript

    run = paths_for(args.manuscript, args.run_dir)
    outputs = [run.ms_full, run.ms_summary]
    if not outputs_fresh([Path(args.manuscript)], outputs, args.force):
        with run_lock(run.run_dir):
            manuscript = parse_manuscript(args.manuscript)
            _write(run.ms_full, manuscript.to_dict())
            _write(run.ms_summary, manuscript.to_summary_dict())
            update_manifest(run.run_dir, args.manuscript, "parse", outputs)
    _print_ok("parse", run.ms_summary)
    return 0


def _ensure_parse(args) -> Path:
    run = paths_for(args.manuscript, args.run_dir)
    if not run.ms_summary.exists() or args.force:
        _cmd_parse(args)
    return run.run_dir


def _cmd_concepts(args) -> int:
    from .concepts import derive_from_summary

    _ensure_parse(args)
    run = paths_for(args.manuscript, args.run_dir)
    if not outputs_fresh([run.ms_summary], [run.concepts], args.force):
        with run_lock(run.run_dir):
            payload = derive_from_summary(_read_json(run.ms_summary))
            _write(run.concepts, payload)
            update_manifest(run.run_dir, args.manuscript, "concepts", [run.concepts])
    _print_ok("concepts", run.concepts)
    return 0


def _ensure_concepts(args) -> Path:
    run = paths_for(args.manuscript, args.run_dir)
    if not run.concepts.exists() or args.force:
        _cmd_concepts(args)
    return run.run_dir


def _cmd_profile(args) -> int:
    from .profile import build_profile

    _ensure_concepts(args)
    run = paths_for(args.manuscript, args.run_dir)
    outputs = [run.profile]
    if not outputs_fresh([run.ms_summary, run.concepts], outputs, args.force):
        with run_lock(run.run_dir):
            payload = build_profile(
                _read_json(run.ms_summary),
                _read_json(run.concepts),
                oa_preference=getattr(args, "oa_preference", "any"),
            )
            _write(run.profile, payload)
            update_manifest(run.run_dir, args.manuscript, "profile", outputs)
    _print_ok("profile", run.profile)
    return 0


def _ensure_profile(args) -> Path:
    run = paths_for(args.manuscript, args.run_dir)
    if not run.profile.exists() or args.force:
        _cmd_profile(args)
    return run.run_dir


def _cmd_contribution(args) -> int:
    from .contribution import assess_contribution

    _ensure_profile(args)
    run = paths_for(args.manuscript, args.run_dir)
    outputs = [run.contribution]
    inputs = [run.ms_summary, run.ms_full, run.profile]
    if not outputs_fresh(inputs, outputs, args.force):
        with run_lock(run.run_dir):
            payload = assess_contribution(
                _read_json(run.ms_summary),
                _read_json(run.profile),
                _read_json(run.ms_full) if run.ms_full.exists() else None,
            )
            _write(run.contribution, payload)
            update_manifest(run.run_dir, args.manuscript, "contribution", outputs)
    _print_ok("contribution", run.contribution)
    return 0


def _ensure_contribution(args) -> Path:
    run = paths_for(args.manuscript, args.run_dir)
    if not run.contribution.exists() or args.force:
        _cmd_contribution(args)
    return run.run_dir


def _cmd_specialty(args) -> int:
    from .specialty import build_specialty_plan, seed_venues_from_plan

    _ensure_contribution(args)
    run = paths_for(args.manuscript, args.run_dir)
    outputs = [run.specialty_queries, run.specialty_venues]
    inputs = [run.ms_summary, run.concepts, run.profile, run.contribution]
    if not outputs_fresh(inputs, outputs, args.force):
        with run_lock(run.run_dir):
            plan = build_specialty_plan(
                _read_json(run.ms_summary),
                _read_json(run.profile),
                _read_json(run.concepts),
                broad=getattr(args, "strategy", "balanced") == "broad",
            )
            _write(run.specialty_queries, plan)
            _write(run.specialty_venues, [hit.to_dict() for hit in seed_venues_from_plan(plan)])
            update_manifest(run.run_dir, args.manuscript, "specialty", outputs)
    _print_ok("specialty", run.specialty_queries)
    return 0


def _ensure_specialty(args) -> Path:
    run = paths_for(args.manuscript, args.run_dir)
    if not run.specialty_queries.exists() or not run.specialty_venues.exists() or args.force:
        _cmd_specialty(args)
    return run.run_dir


def _cmd_venues(args) -> int:
    from .venues import search_venues

    if args.run_dir:
        run = paths_for(None, args.run_dir)
    elif getattr(args, "manuscript", None):
        run = paths_for(args.manuscript, None)
    else:
        run = None
    if args.out:
        out_path = Path(args.out)
    elif run:
        out_path = run.run_dir / query_filename(args.query)
    else:
        raise ValueError("sn venues needs --manuscript, --run-dir, or --out")
    if not outputs_fresh([], [out_path], args.force):
        hits = search_venues(args.query, per_page=args.per_page, venue_types=tuple(args.venue_types))
        _write(out_path, [hit.to_dict() for hit in hits])
        if run:
            update_manifest(run.run_dir, getattr(args, "manuscript", None), "venues", [out_path])
    _print_ok("venues", out_path)
    return 0


def _collect_venue_files(run_dir: Path) -> list[Path]:
    files = sorted(run_dir.glob("venues_*.json"))
    specialty = run_dir / "specialty_venues.json"
    if specialty.exists():
        files.append(specialty)
    return files


def _cmd_rank(args) -> int:
    from .ranking import rank_venues, summarize_bucketed
    from .venues import VenueHit, _merge_hits

    _ensure_contribution(args)
    run = paths_for(args.manuscript, args.run_dir)
    concepts_payload = _read_json(run.concepts)
    concepts = concepts_payload.get("concepts") if isinstance(concepts_payload, dict) else []
    venue_files = [Path(path) for path in args.venues_json] if args.venues_json else _collect_venue_files(run.run_dir)
    if not venue_files:
        raise FileNotFoundError("No venue JSON files found; run sn venues or sn strategist first")
    suffix = strategy_suffix(args.strategy, args.oa_preference)
    ranked_out = run.run_dir / f"ranked_{suffix}.json"
    agent_out = run.run_dir / f"ranked_agent_{suffix}.json"
    bucketed_out = run.run_dir / f"ranked_buckets_{suffix}.json"
    inputs = [run.concepts, run.ms_summary, run.profile, run.contribution, *venue_files]
    if not outputs_fresh(inputs, [ranked_out, agent_out, bucketed_out], args.force):
        loaded_venues = []
        for path in venue_files:
            for row in _read_json(path):
                loaded_venues.append(VenueHit(**row))
        venues = _merge_hits([], loaded_venues)
        summary = _read_json(run.ms_summary)
        ranked = rank_venues(
            concepts,
            venues,
            apc_budget_usd=args.apc_budget,
            strategy=args.strategy,
            oa_preference=args.oa_preference,
            ms_title=summary.get("title"),
            ms_abstract=summary.get("abstract"),
            contribution_assessment=_read_json(run.contribution),
        )
        _write(ranked_out, [item.to_dict() for item in ranked])
        bucketed = summarize_bucketed(ranked, strategy=args.strategy, top_n=args.agent_top_n)
        _write(bucketed_out, bucketed)
        _write(agent_out, bucketed)
        update_manifest(run.run_dir, args.manuscript, "rank", [ranked_out, bucketed_out, agent_out])
    _print_ok("rank", agent_out)
    return 0


def _cmd_strategist(args) -> int:
    from .concepts import build_queries

    _ensure_concepts(args)
    _ensure_contribution(args)
    _ensure_specialty(args)
    run = paths_for(args.manuscript, args.run_dir)
    concepts_payload = _read_json(run.concepts)
    concepts = concepts_payload.get("concepts", [])
    base_queries = list(concepts_payload.get("queries") or build_queries(concepts))
    specialty_plan = _read_json(run.specialty_queries)
    queries = base_queries[: args.max_queries]
    for query in specialty_plan.get("queries") or []:
        if query not in queries:
            queries.append(query)
        if len(queries) >= args.max_queries + args.max_specialty_queries:
            break
    for row in (specialty_plan.get("seed_journals") or [])[: args.max_seed_queries]:
        journal = row.get("journal")
        if journal and journal not in queries:
            queries.append(journal)
    if not args.venues_json:
        for query in queries:
            venue_args = argparse.Namespace(
                query=query,
                per_page=args.per_page,
                venue_types=args.venue_types,
                out=None,
                run_dir=str(run.run_dir),
                manuscript=args.manuscript,
                force=args.force,
            )
            _cmd_venues(venue_args)
    _cmd_rank(args)
    suffix = strategy_suffix(args.strategy, args.oa_preference)
    agent_out = run.run_dir / f"ranked_agent_{suffix}.json"
    _print_ok("strategist", agent_out)
    if not args.quiet:
        emit_json(_read_json(agent_out))
    return 0


def _cmd_rules(args) -> int:
    from .rules import _extract_rules, fetch_rules

    if args.from_file:
        html = Path(args.from_file).read_text(encoding="utf-8")
        rules = _extract_rules(args.journal, args.url or f"file://{Path(args.from_file).resolve()}", html)
    else:
        if not args.url:
            raise ValueError("rules requires a URL unless --from-file is provided")
        rules = fetch_rules(args.journal, args.url, refresh=args.refresh, offline=args.offline)
    out_path = Path(args.out) if args.out else Config.load().rules_dir / f"{slug(args.journal)}.json"
    _write(out_path, rules.to_dict())
    _print_ok("rules", out_path)
    return 0


def _cmd_check(args) -> int:
    from .figures import check_against_rules, extract_figures_from_pdf
    from .parse import parse_manuscript
    from .rules import JournalRules

    run = paths_for(args.manuscript, args.run_dir)
    rules_path = Path(args.rules_json) if args.rules_json else Config.load().rules_dir / f"{slug(args.journal)}.json"
    rules = JournalRules(**_read_json(rules_path))
    manuscript = parse_manuscript(args.manuscript)
    figures = extract_figures_from_pdf(args.manuscript) if Path(args.manuscript).suffix.casefold() == ".pdf" else []
    result = check_against_rules(figures, rules, manuscript.word_count)
    out_path = run.run_dir / f"check_{slug(args.journal)}.json"
    _write(out_path, {"figures": [fig.to_dict() for fig in figures], "check": result.to_dict()})
    update_manifest(run.run_dir, args.manuscript, "check", [out_path])
    _print_ok("check", out_path)
    return 0


def _cmd_triage(args) -> int:
    from .revision import build_response_skeleton, parse_reviewer_comments

    text = Path(args.comments_file).read_text(encoding="utf-8")
    items = parse_reviewer_comments(text)
    payload = {"items": items, "skeleton": build_response_skeleton(items)}
    if args.out:
        out_path = Path(args.out)
    elif getattr(args, "manuscript", None):
        run = paths_for(args.manuscript, args.run_dir)
        out_path = run.run_dir / "triage.json"
        payload["manuscript"] = str(Path(args.manuscript).resolve())
    else:
        out_path = Path(args.comments_file).with_suffix(".triage.json")
    _write(out_path, payload)
    if getattr(args, "manuscript", None):
        run = paths_for(args.manuscript, args.run_dir)
        update_manifest(run.run_dir, args.manuscript, "triage", [out_path])
    _print_ok("triage", out_path)
    return 0


def _cmd_config(args) -> int:
    if args.config_action == "show":
        cfg = Config.load()
        payload = {
            "scopus_key": _masked(cfg.key("scopus_key")),
            "doaj_key": _masked(cfg.key("doaj_key")),
            "openalex_email": cfg.key("openalex_email"),
            "crossref_email": cfg.key("crossref_email"),
            "config_dir": str(cfg.config_dir),
        }
        emit_json(payload)
        return 0
    if args.store == "env":
        _write_dotenv_value(args.key, args.value or "")
    else:
        cfg = Config.load()
        canonical = _canonical_key(args.key)
        if canonical is None:
            raise ValueError(f"Unknown key: {args.key}")
        setattr(cfg, canonical, args.value)
        cfg.save()
    _print_ok("config", Config.load().config_dir)
    return 0


def _probe_dep(name: str) -> bool:
    import importlib

    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _cmd_doctor(args) -> int:
    import os
    from .publisher_risk import RISK_FILENAME

    cfg = Config.load()
    publisher_risk_path = cfg.config_dir / RISK_FILENAME
    deps = {name: _probe_dep(name) for name in
            ("httpx", "fitz", "docx", "PIL", "pydantic", "rapidfuzz")}
    payload = {
        "version": __version__,
        "sn_home": str(Path(__file__).resolve().parents[2]),
        "config_dir": str(cfg.config_dir),
        "cache_dir": str(cfg.cache_dir),
        "rules_dir": str(cfg.rules_dir),
        "publisher_risk_path": str(publisher_risk_path),
        "publisher_risk_configured": publisher_risk_path.exists(),
        "writable_config": os.access(cfg.config_dir, os.W_OK),
        "writable_cache": os.access(cfg.cache_dir, os.W_OK),
        "deps": deps,
        "ok": all(deps.values()) and os.access(cfg.config_dir, os.W_OK),
    }
    emit_json(payload)
    _print_ok("doctor", cfg.config_dir)
    return 0


def _cmd_runs(args) -> int:
    if args.runs_action == "ls":
        emit_json(list_runs())
        return 0
    if args.runs_action == "path":
        _print_ok("runs", paths_for(args.manuscript, args.run_dir).run_dir)
        return 0
    removed = clean_runs(args.older_than)
    emit_json({"removed": removed})
    return 0


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sn")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--run-dir")
        p.add_argument("--force", action="store_true")
        p.add_argument("-q", "--quiet", action="store_true")
        p.add_argument("-v", "--verbose", action="store_true")
        p.add_argument("--json", dest="json_progress", action="store_true",
                       help="Emit machine-readable progress on stderr.")

    p = sub.add_parser("parse")
    add_common(p)
    p.add_argument("manuscript")
    p.set_defaults(func=_cmd_parse)

    p = sub.add_parser("concepts")
    add_common(p)
    p.add_argument("manuscript")
    p.set_defaults(func=_cmd_concepts)

    p = sub.add_parser("profile")
    add_common(p)
    p.add_argument("manuscript")
    p.add_argument("--oa-preference", default="any", choices=["any", "oa-only", "avoid-oa"])
    p.set_defaults(func=_cmd_profile)

    p = sub.add_parser("contribution")
    add_common(p)
    p.add_argument("manuscript")
    p.add_argument("--oa-preference", default="any", choices=["any", "oa-only", "avoid-oa"])
    p.set_defaults(func=_cmd_contribution)

    p = sub.add_parser("specialty")
    add_common(p)
    p.add_argument("manuscript")
    p.add_argument("--strategy", default="balanced", choices=["balanced", "ambitious", "safe", "fast", "low-cost", "oa-only", "broad"])
    p.add_argument("--oa-preference", default="any", choices=["any", "oa-only", "avoid-oa"])
    p.set_defaults(func=_cmd_specialty)

    p = sub.add_parser("venues")
    add_common(p)
    p.add_argument("query")
    p.add_argument("--manuscript")
    p.add_argument("--per-page", type=int, default=40)
    p.add_argument("--venue-types", nargs="+", default=["journal"],
                   choices=["journal", "conference"])
    p.add_argument("--out")
    p.set_defaults(func=_cmd_venues)

    p = sub.add_parser("rank")
    add_common(p)
    p.add_argument("manuscript")
    p.add_argument("--venues-json", nargs="*", default=[])
    p.add_argument("--strategy", default="balanced", choices=["balanced", "ambitious", "safe", "fast", "low-cost", "oa-only", "broad"])
    p.add_argument("--apc-budget", type=float)
    p.add_argument("--oa-preference", default="any", choices=["any", "oa-only", "avoid-oa"])
    p.add_argument("--agent-top-n", type=int, default=12)
    p.set_defaults(func=_cmd_rank)

    p = sub.add_parser("strategist")
    add_common(p)
    p.add_argument("manuscript")
    p.add_argument("--strategy", default="balanced", choices=["balanced", "ambitious", "safe", "fast", "low-cost", "oa-only", "broad"])
    p.add_argument("--apc-budget", type=float)
    p.add_argument("--oa-preference", default="any", choices=["any", "oa-only", "avoid-oa"])
    p.add_argument("--venue-types", nargs="+", default=["journal"],
                   choices=["journal", "conference"])
    p.add_argument("--per-page", type=int, default=40)
    p.add_argument("--agent-top-n", type=int, default=12)
    p.add_argument("--max-queries", type=int, default=4)
    p.add_argument("--max-specialty-queries", type=int, default=3)
    p.add_argument("--max-seed-queries", type=int, default=5)
    p.add_argument("--venues-json", nargs="*", default=[])
    p.set_defaults(func=_cmd_strategist)

    p = sub.add_parser("rules")
    p.add_argument("journal")
    p.add_argument("url", nargs="?")
    p.add_argument("--from-file")
    p.add_argument("--out")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.set_defaults(func=_cmd_rules)

    p = sub.add_parser("check")
    add_common(p)
    p.add_argument("manuscript")
    p.add_argument("--journal", required=True)
    p.add_argument("--rules-json")
    p.set_defaults(func=_cmd_check)

    p = sub.add_parser("triage")
    p.add_argument("comments_file")
    p.add_argument("--manuscript")
    p.add_argument("--run-dir")
    p.add_argument("--out")
    p.set_defaults(func=_cmd_triage)

    p = sub.add_parser("config")
    config_sub = p.add_subparsers(dest="config_action", required=True)
    show = config_sub.add_parser("show")
    show.set_defaults(func=_cmd_config)
    setp = config_sub.add_parser("set")
    setp.add_argument("--key", required=True)
    setp.add_argument("--value", required=True)
    setp.add_argument("--store", choices=["env", "config"], default="env")
    setp.set_defaults(func=_cmd_config)

    p = sub.add_parser("doctor")
    p.set_defaults(func=_cmd_doctor)

    p = sub.add_parser("home")
    p.set_defaults(func=_print_home)

    p = sub.add_parser("runs")
    runs_sub = p.add_subparsers(dest="runs_action", required=True)
    ls = runs_sub.add_parser("ls")
    ls.set_defaults(func=_cmd_runs)
    path = runs_sub.add_parser("path")
    path.add_argument("manuscript")
    path.add_argument("--run-dir")
    path.set_defaults(func=_cmd_runs)
    clean = runs_sub.add_parser("clean")
    clean.add_argument("--older-than", type=int, default=30, help="Age in days.")
    clean.set_defaults(func=_cmd_runs)
    return ap


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"INPUT {exc}", file=sys.stderr)
        return EXIT_INPUT
    except (ValueError, KeyError, argparse.ArgumentError) as exc:
        print(f"USAGE {exc}", file=sys.stderr)
        return EXIT_USER
    except Exception as exc:
        if _looks_like_network_error(exc):
            print(f"EXTERNAL {exc}", file=sys.stderr)
            return EXIT_EXTERNAL
        print(f"ERROR {exc}", file=sys.stderr)
        return EXIT_INTERNAL


def _looks_like_network_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if name.startswith(("HTTP", "Connect", "Timeout", "Network", "Remote")):
        return True
    try:
        import httpx

        if isinstance(exc, httpx.HTTPError):
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    raise SystemExit(main())
