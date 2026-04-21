# submission-navigator
Plugin for academic submission workflow.

## Skills
- `sn-config` — one-time setup (API keys, email).
- `submission-strategist` — rank journals for a manuscript.
- `journal-rules` — fetch + summarize author guidelines.
- `format-checker` — check figures/tables/text vs journal rules.
- `mock-revision` — draft revision response letters.

## Install (manual)
1. Install [`uv`](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`).
2. Clone into `~/.claude/plugins/submission-navigator`.
3. `cd scripts && uv sync` (creates `.venv`, installs deps from `uv.lock`).
4. Restart your agent host. Skills auto-discovered. Skills invoke helpers via `uv run --project scripts python -m sn_lib.<module>`.

## First use
Run the `sn-config` skill to store an OpenAlex email (recommended).

## Data sources
- OpenAlex (no key; email for polite pool)
- DOAJ (no key)
- Crossref (email optional)
- Scopus (key optional)

## Limitations (MVP)
- No browser form-filling.
- Figure DPI detection requires PDF source.
- Rule extraction is heuristic; always verify against the journal's own page.
