# submission-nav

`submission-nav` is an early-preview GitHub skill project for academic submission workflow support.

It gives an AI coding agent reusable workflows for journal targeting, author-rule lookup, manuscript format checks, and submission/revision planning. Local helper code runs underneath the skill when deterministic parsing, API lookup, caching, or scoring is needed.

This is decision-support software, not an automatic journal selector. Always verify final journal policies, fees, indexing, and scope on the publisher's official site before submission.

## Capabilities

- Journal and venue targeting from PDF/DOCX manuscripts
  - can target journals, conferences, or both
  - supports strategy-aware ordering such as balanced, ambitious, safe, fast, low-cost, OA-only, or broad exploration
- Journal author-rule fetching and local caching
- Format checks against cached journal rules
- Pre-submission revision planning
- Reviewer-comment triage and response-letter drafting

## Install

### Recommended: npx skills

Install the self-contained toolkit skill with:

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

## First use

After installing the skill, ask your agent to use `submission-nav` and run the setup check. Then use the `sn-config` workflow to save optional credentials in the installed skill's repo-local `.env`.

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

- Rule extraction is heuristic and must be checked against the journal's official page.
- Figure DPI detection is strongest when the manuscript is available as PDF.
- Review planning and response-letter drafting are intentionally separate steps.

## Known Limitations

- Publisher sites may block automated fetching, require JavaScript, or show cookie/interstitial pages.
- Journal metadata, APCs, OA status, and ranking signals can be incomplete or stale.
- Venue recommendations are probabilistic decision support. They are not acceptance predictions.
- Broad journals and megajournals can be hard to rank because their scope is intentionally wide.
- Conference support is currently strongest for computer-science-style venues available through OpenAlex/DBLP metadata.
- Users should not submit based only on cached rules; always inspect the live author instructions.

## Development

Run focused tests from the repository root:

```bash
uv run --project scripts python -m pytest
```

Generated evaluation artifacts belong under `temp_sn/`, which is ignored by git.
