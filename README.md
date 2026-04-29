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

## Install

### npx skills

Install the self-contained toolkit skill.

For Codex:

```bash
npx skills add https://github.com/qwerty239qwe/submission-nav --skill submission-nav -a codex
```

For Claude Code:

```bash
npx skills add https://github.com/qwerty239qwe/submission-nav --skill submission-nav -a claude-code
```

For a local checkout, replace the URL with `.` (and pass the same `-a` flag for your agent):

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

After installing, ask your agent to use `submission-nav` and run `sn doctor` to confirm the helper runtime is healthy. Then save any optional API credentials you have:

> "Use submission-nav to set my OpenAlex email to me@example.com and my Elsevier API key."

The agent will route that through the `sn-config` workflow and store values in the repo-local `.env`. Supported keys: `ELSEVIER_API_KEY`, `DOAJ_KEY`, `OPENALEX_EMAIL`, `CROSSREF_EMAIL`. An example file is at [`.env.example`](.env.example).

## How to Use

Talk to your agent in natural language and name the skill. The agent picks the right sub-workflow and runs `sn` commands underneath. Common scenarios:

### Find a venue for a manuscript

> "Use submission-nav. Where should I submit `~/papers/draft.pdf`? I want a balanced shortlist."

> "Same manuscript but I have an APC budget of 1500 USD and prefer open access."

> "Treat it as a CS paper and include conferences."

The agent returns a ranked table (fit, risk, impact proxy, OA, APC, h-index), a rationale for the top pick, and a stretch/target/safety ladder. It also caches the run so later questions reuse it.

By default, venue search favors precision over breadth. If you want a wider exploratory pass, ask the agent to use neighbor expansion, or run `sn strategist ... --expand-neighbors`. This performs a second OpenAlex pass from the strongest first-hop venue concepts. It can surface adjacent journals, but it is slower and may add noisy candidates, so it is opt-in rather than default.

#### Strategies

You can ask for a different posture at any time ("rerank with the `safe` strategy"). Each strategy reweights the same underlying signals: topical fit, journal suitability, impact proxy, cost fit, and OA fit.

| Strategy | What it favors | When to use |
|----------|----------------|-------------|
| `balanced` (default) | Suitability + fit, modest weight on impact | First-pass shortlist |
| `ambitious` | Stretch venues with higher impact, accepts more risk | You want a top-tier shot and can absorb a desk reject |
| `safe` | Strong suitability + good article-type fit, light on impact | You need a likely acceptance soon |
| `fast` | Suitability + OA + cost fit, deprioritizes prestige | Time-sensitive submission, no stretch attempts |
| `low-cost` | Heavy weight on cost fit (APC vs budget) | Tight or zero APC budget |
| `oa-only` | Heavy weight on open-access fit | Funder mandates OA |
| `broad` | Wider net, more weight on raw fit and scope/impact | Exploratory survey of where the paper *could* land |

Combine with `--apc-budget <usd>` and `--oa-preference any|oa-only|avoid-oa` for finer control.

### Pull author instructions

> "Use submission-nav to fetch author rules for *PLOS ONE* and *Scientific Reports* and compare them."

If a publisher page blocks automated fetching, the agent will ask for a copy of the guidelines text and re-run with `--from-file`.

### Pre-submission format check

> "Check whether `draft.pdf` is ready for submission to PLOS ONE."

The agent runs the format checker against the cached rules and reports `Violations`, `Warnings`, and `OK` items with concrete fixes.

### Plan a revision before you submit

> "Read `draft.pdf` and tell me what reviewers will likely complain about. Give me a prioritized list."

The agent produces critical fixes, strong improvements, optional polish, and predicted reviewer objections, all tied to specific sections.

### Triage reviewer comments

> "Reviewer comments are in `reviews.txt` and the manuscript is `draft.pdf`. Triage the comments and tell me where to spend effort."

Returns a per-comment table with theme, priority, effort, strategy (accept / partially / clarify / rebut / needs author input), and a materials checklist.

### Draft a response letter

> "Using `reviews.txt` and the notes in `revision-notes.md`, draft a response letter."

The agent produces a Markdown response letter, marking unresolved items as `[NEED INPUT]`.

### Pick up where you left off

> "What runs do we have cached?" - `sn runs ls`
>
> "Re-rank that manuscript with the `safe` strategy." - reuses the cached parse + venues
>
> "Force a fresh fetch." - adds `--force`

## Direct CLI Use

The `sn` command is also available for direct local use, without an agent. The main commands are:

```bash
sn doctor                                                # health check
sn strategist manuscript.docx --strategy balanced        # full pipeline
sn strategist manuscript.docx --expand-neighbors         # broader, slower exploratory venue retrieval
sn rules "PLOS ONE" "https://journals.plos.org/plosone/s/submission-guidelines"
sn check manuscript.pdf --journal plos-one
sn triage reviews.txt --manuscript manuscript.pdf
sn runs ls                                               # list cached runs
sn config show
```

Run `sn --help` or `sn <verb> --help` for the full surface. Outputs land in a manuscript-hash-keyed run cache under your config dir, so chained commands compose without juggling temp paths.

## How It Works

The skill instructions tell the agent which `sn` verb to use for each scenario; `sn` calls into local helpers that parse manuscripts, retrieve venue metadata, cache journal rules, and run format checks. The runtime is an implementation detail you should not normally need to manage.

## Data sources

- OpenAlex
- DOAJ
- Crossref
- Elsevier
- DBLP

Conference support is currently aimed at computer-science-style venue discovery through OpenAlex source types, with DBLP used for conference name/acronym normalization when available. Conference-specific ranking sources such as CORE are not integrated yet.

OpenAlex requests can be rate-limited or quota-limited. Configure `OPENALEX_EMAIL` so requests are attributable, and treat temporary `HTTP 429` failures as a data-source availability issue rather than a manuscript-ranking result.

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
- Neighbor expansion is useful for discovery but not always better for ranking; keep it for broad searches or manual exploration.

## Development

Run focused tests from the repository root:

```bash
uv run --project scripts python -m pytest
```

Generated evaluation artifacts belong under `temp_sn/`, which is ignored by git.

The public cross-field evaluation helper samples recent OpenAlex works by default, using the calendar window from January 1 five years ago through today. For example, on April 30, 2026 the default window is `2021-01-01` through `2026-04-30`.
