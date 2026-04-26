# submission-nav

`submission-nav` is a local skill/plugin set for academic submission workflow support.

It is designed to feel like a reusable agent capability first, with local helper code running underneath when needed.

## Included skills

- `sn-config` - set up API credentials
- `submission-strategist` - rank journal targets for a manuscript
  - can target journals, conferences, or both
  - supports strategy-aware ordering such as balanced, ambitious, safe, fast, low-cost, OA-only, or broad exploration
- `journal-rules` - fetch and summarize author instructions
- `format-checker` - check manuscript figures/text against cached journal rules
- `pre-submission-revision` - prioritize manuscript improvements before submission
- `review-revision-strategist` - triage reviewer comments and plan revisions
- `response-letter-drafter` - draft point-by-point response letters

## Install

1. Place this repository where your agent host loads local skills or plugins.
2. Run the one-time setup script:
   - Windows: [bin/install.ps1](bin/install.ps1)
   - macOS / Linux: [bin/install.sh](bin/install.sh)
3. Restart the agent host so the skills reload.

The setup script prepares the local helper runtime for the skills. Users should not need to manage the Python environment manually during normal use.

## First use

Run `sn-config` to save optional credentials in the repo-local `.env`.

Supported environment variables:

- `ELSEVIER_API_KEY`
- `DOAJ_KEY`
- `OPENALEX_EMAIL`
- `CROSSREF_EMAIL`

An example file is included at [`.env.example`](.env.example).

## What The Skills Use Internally

The skills call local helper commands to parse manuscripts, retrieve venue metadata, cache journal rules, and run format checks. That runtime is an implementation detail of the plugin and should not normally matter to end users.

## Data sources

- OpenAlex
- DOAJ
- Crossref
- Elsevier
- DBLP

Conference support is currently aimed at computer-science-style venue discovery through OpenAlex source types, with DBLP used for conference name/acronym normalization when available. Conference-specific ranking sources such as CORE are not integrated yet.

## Notes

- Rule extraction is heuristic and should still be checked against the journal's official page.
- Figure DPI detection is strongest when the manuscript is available as PDF.
- Review planning and response-letter drafting are intentionally separate steps.

## Docs

- Refactor plan: [docs/refactor-plan.md](docs/refactor-plan.md)
- Developer setup and internals: [docs/development.md](docs/development.md)
- Verification process: [docs/verification.md](docs/verification.md)
