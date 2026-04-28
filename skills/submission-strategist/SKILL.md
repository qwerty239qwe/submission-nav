---
name: submission-strategist
description: Use when the user wants journal or venue recommendations for a manuscript, asks where to submit, or provides a PDF or DOCX and wants ranked submission targets.
---

# submission-strategist

This skill turns a manuscript into a ranked list of candidate journals or conference venues.

## Inputs

Required:
- manuscript path in PDF or DOCX format

Optional:
- `--strategy`: `balanced`, `ambitious`, `safe`, `fast`, `low-cost`, `oa-only`, or `broad`
- `--venue-types`: `journal`, `conference`, or both
- `--apc-budget <usd>`
- `--oa-preference`: `any`, `oa-only`, or `avoid-oa`

Ask for the manuscript path if it is missing.

## Procedure

1. Run the chained workflow:

```bash
sn strategist "<manuscript>" --strategy balanced --venue-types journal --agent-top-n 12
```

Use the user's stated posture instead of manually spending tokens to re-rank. Examples:

```bash
sn strategist "<manuscript>" --strategy safe --oa-preference avoid-oa
sn strategist "<manuscript>" --strategy ambitious --venue-types journal conference
sn strategist "<manuscript>" --strategy broad --venue-types conference --agent-top-n 20
```

2. Read the compact ranked summary path printed by the command. Use the full ranked JSON only when the compact summary looks thin or the user asks for a broader candidate set.

3. Use the bucketed output as the primary decision structure. The chained workflow writes a manuscript profile (`ms_profile.json`) and bucketed ranked summaries (`ranked_agent_<strategy>.json` and `ranked_buckets_<strategy>.json`) with:
- `stretch`: plausible higher-impact options
- `target`: strongest balance of fit and suitability
- `safe`: lower-risk fallbacks
- `fallback`: weak-score or caution cases
- `avoid`: article-type, scope, or publisher-integrity mismatches

4. Screen obvious article-type mismatches before presenting results:
- review journals for original research
- method journals for papers without a new method
- data/resource journals for non-resource papers
- elite broad-scope journals when the manuscript lacks correspondingly broad novelty

5. Present a decision-oriented result.

## Output

Return:
- a Markdown table of the top 5 to 10 venues
- the strategy used
- a short rationale for the top pick
- a submission ladder from the generated buckets: stretch, target, safe
- caveats such as APC conflict, weak scope evidence, partial metadata enrichment, or low-confidence parsing
- saved ranked-summary path for reuse

Recommended table columns:
- rank
- venue
- publisher
- fit
- risk
- impact proxy
- OA
- APC
- h-index

## Failure Handling

- If parsing fails, ask for a cleaner PDF or original DOCX.
- If venue retrieval is weak, rerun once with `--strategy broad` or broader concepts.
- If the user wants CS targeting, use `--venue-types conference` or `journal conference`.
- If external data sources fail, say which sources failed and continue with available evidence.
- Do not fabricate APCs, journal policies, indexing status, or acceptance likelihood.

## Handoff

- Use `journal-rules` after the user selects targets.
- Use `format-checker` after target rules are cached.
