# Changelog

## Unreleased

## 0.1.1 - 2026-05-08

- Improved PDF title and abstract extraction for journal-header and arXiv-style first pages.
- Added content-derived concept boosts for electrocatalysis, cybersecurity economics, game theory, and AI/security arms-race manuscripts.
- Fixed false bioinformatics classification caused by matching `omics` inside `economics`.
- Added broader chemistry/electrocatalysis and cybersecurity/economics domain signals for venue compatibility.
- Added published-target miss diagnostics to the public cross-field evaluation helper.
- Tightened bucketed recommendation display so hard exclusions stay out of visible top results and bucket diversity is preserved.
- Added regression coverage for RSC, arXiv, electrocatalysis, cybersecurity economics, domain-gating, and bucket-rescue behavior.

## 0.1.0 - 2026-04-30

- **Breaking**: removed `python -m sn_lib.<module>` CLIs. Use the canonical `sn` dispatcher (`sn parse`, `sn rank`, `sn rules`, `sn config`, etc.) or the bundled `bin/sn` (`bin/sn.cmd` on Windows).
- Added `sn` CLI with atomic verbs (`parse`, `concepts`, `venues`, `rank`, `rules`, `check`, `triage`, `config`), chained verbs (`strategist`), and meta verbs (`doctor`, `home`, `runs`).
- Added manuscript-hash-keyed run cache under `<config_dir>/runs/<hash>/` with cross-platform locking and stale-lock reclaim.
- Added `--from-file` to `sn rules` for blocked-fetch fallback.
- Added `--manuscript` and `--run-dir` to `sn triage` so triage output can land in the run cache.
- Added strategy-aware venue suitability checks for article type, contribution level, OA/cost, and local publisher-risk lists.
- Added CS conference discovery through OpenAlex source types and DBLP metadata normalization.
- Added optional OpenAlex neighbor expansion with `--expand-neighbors` for broader venue discovery.
- Added recent-paper public cross-field evaluation helpers with explicit OpenAlex quota/error reporting.
- Added GitHub Actions test CI.
- Tightened skill prose to reference `sn` instead of `uv run python -m sn_lib.*`.

## Pre-release - 2026-04-21

- Initial release: sn-config, submission-strategist, journal-rules, format-checker, mock-revision.
