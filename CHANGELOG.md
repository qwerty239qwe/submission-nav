# Changelog

## Unreleased
- **Breaking**: removed `python -m sn_lib.<module>` CLIs. Use the canonical `sn` dispatcher (`sn parse`, `sn rank`, `sn rules`, `sn config`, etc.) or the bundled `bin/sn` (`bin/sn.cmd` on Windows).
- Added `sn` CLI with atomic verbs (`parse`, `concepts`, `venues`, `rank`, `rules`, `check`, `triage`, `config`), chained verbs (`strategist`), and meta verbs (`doctor`, `home`, `runs`).
- Added manuscript-hash-keyed run cache under `<config_dir>/runs/<hash>/` with cross-platform locking and stale-lock reclaim.
- Added `--from-file` to `sn rules` for blocked-fetch fallback.
- Added `--manuscript` and `--run-dir` to `sn triage` so triage output can land in the run cache.
- `sn doctor` now reports dependency probes, writable-dir status, and an `ok` flag.
- Tightened skill prose to reference `sn` instead of `uv run python -m sn_lib.*`.

## 0.1.0 — 2026-04-21
- Initial release: sn-config, submission-strategist, journal-rules, format-checker, mock-revision.
