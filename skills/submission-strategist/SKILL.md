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

3. Use the specialty-expanded candidate pool before judging results. The chained workflow writes:
- `ms_profile.json`: manuscript profile used for article-type and scope gates
- `contribution_assessment.json`: deterministic contribution tier, strengths, limitations, and ambition bands
- `specialty_queries.json`: detected specialty domains, added search queries, and seed journals
- `specialty_venues.json`: high-recall specialty seed venues that enter ranking even if API keyword search misses them
- `ranked_agent_<strategy>.json` and `ranked_buckets_<strategy>.json`: final bucketed recommendations

Inspect `contribution_assessment.json` if the recommendation ladder looks too ambitious or too conservative. Inspect `specialty_queries.json` if the final venues look generic. If obvious field journals are missing, rerun with `--strategy broad` or broaden the manuscript-specific query.

4. Use contribution and ambition alignment before presenting stretch options:
- `exploratory`: emphasize safe or broad fallback venues
- `solid_specialty`: emphasize specialty targets and conservative selective-specialty stretch venues
- `strong_specialty`: allow selective specialty and some high-impact specialty venues
- `high_impact_specialty`: allow high-impact specialty venues
- `elite_general`: only then treat elite general/top clinical venues as serious options

Do not present elite general/top clinical venues as realistic if the contribution assessment marks those bands as avoid.

5. Use the bucketed output as the primary decision structure:
- `stretch`: plausible higher-impact options
- `target`: strongest balance of fit and suitability
- `safe`: lower-risk fallbacks
- `fallback`: weak-score or caution cases
- `avoid`: article-type, scope, or publisher-integrity mismatches

6. Screen obvious article-type mismatches before presenting results:
- review journals for original research
- method journals for papers without a new method
- data/resource journals for non-resource papers
- elite broad-scope journals when the manuscript lacks correspondingly broad novelty

7. Present a decision-oriented result.

## Output

Return:
- a Markdown table of the top 5 to 10 venues
- the strategy used
- the contribution tier and one-sentence implication for ambition
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
- If venue retrieval is weak, first inspect `specialty_queries.json`, then rerun once with `--strategy broad` or broader concepts.
- If the user wants CS targeting, use `--venue-types conference` or `journal conference`.
- If external data sources fail, say which sources failed and continue with available evidence.
- Do not fabricate APCs, journal policies, indexing status, or acceptance likelihood.

## Handoff

- Use `journal-rules` after the user selects targets.
- Use `format-checker` after target rules are cached.
