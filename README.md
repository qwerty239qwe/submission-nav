# submission-nav

`submission-nav` helps AI coding agents support academic submission workflows from manuscript triage to journal targeting and revision planning.

It combines reusable skill instructions with local helper tools for manuscript parsing, venue metadata lookup, author-guideline caching, format checks, and strategy-aware ranking. The goal is to turn "where should I submit this?" into a structured shortlist with visible tradeoffs instead of a one-off guess.

The skill is designed for practical decision support: it can suggest likely venues, flag scope or article-type risks, compare author instructions, and prepare next-step submission work. Final journal policies, fees, indexing, and scope should still be confirmed on the publisher's official site before submission.

## Capabilities

- Journal and venue targeting from PDF/DOCX manuscripts
  - can target journals, conferences, or both
  - supports strategy-aware ordering such as balanced, ambitious, safe, fast, low-cost, OA-only, or broad exploration
- Journal author-rule fetching and local caching
- Format checks against cached journal rules
- Pre-submission revision planning
- Reviewer-comment triage and response-letter drafting

## Example Uses

- "Use `submission-nav` to recommend journals for this manuscript."
- "Find author instructions for my top three target journals."
- "Check whether my manuscript and figures look ready for this journal."
- "Help me choose between a high-impact stretch journal and a safer fallback."
- "Draft a revision plan from these reviewer comments."

## Install

### npx skills

Install the self-contained toolkit skill:

```bash
npx skills add <repo-url> --skill submission-nav -a codex
```

For a local checkout:

```bash
npx skills add . --skill submission-nav -a codex
```

Use `--copy` if symlinks are inconvenient on your platform. For local-path installs, run from a clean checkout or remove local `temp_sn/` outputs first; installing from a Git URL only includes tracked project files.

The recommended `npx skills add` target is the root `submission-nav` skill. The repository also contains internal workflow files under `skills/`, but installing one of those directly may omit the helper runtime under `scripts/`.

### Manual

1. Place this repository where your agent host loads local skills or plugins.
2. Run the one-time setup script:
   - Windows: [bin/install.ps1](bin/install.ps1)
   - macOS / Linux: [bin/install.sh](bin/install.sh)
3. Restart the agent host so the skills reload.

The setup script prepares the local helper runtime for the skills. Users should not need to manage the Python environment manually during normal use.

## First Use

After installing, ask your agent to use `submission-nav` and run the setup check. Then use the `sn-config` workflow to save optional credentials in the installed skill's repo-local `.env`.

Supported environment variables:

- `ELSEVIER_API_KEY`
- `DOAJ_KEY`
- `OPENALEX_EMAIL`
- `CROSSREF_EMAIL`

An example file is included at [`.env.example`](.env.example).

## How It Works

The skills call local helper commands to parse manuscripts, retrieve venue metadata, cache journal rules, and run format checks. That runtime is an implementation detail of the plugin and should not normally matter to end users.

## Data sources

- OpenAlex
- DOAJ
- Crossref
- Elsevier
- DBLP

Conference support is currently aimed at computer-science-style venue discovery through OpenAlex source types, with DBLP used for conference name/acronym normalization when available. Conference-specific ranking sources such as CORE are not integrated yet.

## Practical Notes

- Rule extraction is cached locally and works well for many static author-guideline pages; verify final details on the journal's live page before submission.
- Figure DPI detection is strongest when the manuscript is available as PDF.
- Review planning and response-letter drafting are intentionally separate steps.

## Current Boundaries

- Some publisher pages block automated fetching or require JavaScript; cached rules and manual URLs are supported fallbacks.
- Journal metadata, APCs, OA status, and ranking signals come from public data sources and can be incomplete.
- Venue recommendations are prioritization aids, not acceptance predictions.
- Broad journals and megajournals may need a user-selected strategy such as `safe`, `ambitious`, `low-cost`, or `broad`.
- Conference support is strongest for computer-science-style venues available through OpenAlex and DBLP metadata.

## Development

Run focused tests from the repository root:

```bash
uv run --project scripts python -m pytest
```

Generated evaluation artifacts belong under `temp_sn/`, which is ignored by git.
