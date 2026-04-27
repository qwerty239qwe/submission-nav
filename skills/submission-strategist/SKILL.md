---
name: submission-strategist
description: Use when the user wants journal or venue recommendations for a manuscript, asks where to submit, or provides a PDF or DOCX and wants ranked submission targets.
---

# submission-strategist

This skill helps an agent turn a manuscript into a ranked list of candidate journals or conference venues.

It is designed to be usable from Codex, Claude, Gemini, or any other host that supports reusable skill instructions plus local command execution.

## When to use

Use this skill when the user:
- asks where a manuscript should be submitted
- wants a ranked list of journals, conferences, or venues
- shares a manuscript file and wants fit, impact, or open-access tradeoff analysis

## Required inputs

- A manuscript path in PDF or DOCX format

## Optional inputs

- APC budget in USD
- Open-access-only preference
- journals to exclude
- conferences to include or prefer
- preferred venue type such as `journal`, `conference`, or both
- submission strategy:
  - `balanced` for fit plus reasonable impact, default
  - `ambitious` for higher-impact stretch venues while still flagging risk
  - `safe` for likely-fit venues and lower desk-reject risk
  - `fast` for pragmatic submission when speed matters
  - `low-cost` for APC-sensitive users
  - `oa-only` for open-access-only users
  - `broad` when the user explicitly wants wider exploration
- preferred field, publisher, or impact range

If the manuscript path is missing, ask for it before proceeding.

## Preconditions

1. Ensure local helper dependencies are installed for the repository.
2. If API credentials are needed, run `sn-config` first.
3. Use a writable temp directory for intermediate JSON outputs.
4. If Elsevier enrichment is enabled through `scopus_key`, follow the local policy in `api_rules/elsevier.md` and avoid unnecessary repeated reruns.

## Procedure

1. Parse the manuscript:

```bash
uv run --project scripts python -m sn_lib.parse "<path-to-manuscript>" --out "<temp_dir>/sn_ms.json" --summary-out "<temp_dir>/sn_ms_summary.json"
```

2. Read the compact parsed manuscript summary first and capture:
- title
- abstract
- section headings
- word count
- reference count

Only open the full parsed manuscript JSON if the summary indicates parsing anomalies or you need section text for manual diagnosis.

3. Derive 3 to 5 query concepts from the title and abstract.
- Prefer noun phrases or domain terms.
- Do not send the whole abstract as one query string.
- Use the local concept extractor first:

```bash
uv run --project scripts python -m sn_lib.concepts --summary-json "<temp_dir>/sn_ms_summary.json" --out "<temp_dir>/sn_concepts.json"
```

- Build 2 to 4 short venue-search queries from those concepts, such as endpoint, method, domain, and application framing.
- If ranking signals are weak, broaden once toward venue-facing terms such as `computational toxicology`, `cheminformatics`, `bioinformatics`, `drug safety`, `machine learning conference`, or `data mining conference`.

4. Retrieve candidate venues:

```bash
uv run --project scripts python -m sn_lib.venues "<query-string>" --per-page 40 --venue-types <journal|conference> [<journal|conference> ...] --out "<temp_dir>/sn_venues.json"
```

- Use `journal` by default.
- If the user explicitly wants CS conference targeting, pass `--venue-types conference` or `--venue-types journal conference`.
- Conference candidates are enriched with DBLP name/acronym metadata when available.

5. Rank venues using the derived concepts and the user's submission strategy:

```bash
uv run --project scripts python -m sn_lib.ranking --concepts <c1> <c2> <c3> --venues-json "<temp_dir>/sn_venues.json" --manuscript-summary-json "<temp_dir>/sn_ms_summary.json" --strategy balanced [--apc-budget <usd>] [--oa-preference oa-only] --out "<temp_dir>/sn_ranked.json" --agent-out "<temp_dir>/sn_ranked_agent.json" --agent-top-n 12
```

Use `balanced` unless the user asks for a different posture. Do not solve strategy only by spending more agent tokens on manual filtering; pass the preference into ranking so the full JSON records the scoring assumptions.

6. Review the compact ranked summary first and identify:
- strongest thematic fit
- best overall balance of fit and impact
- lower-risk fallback
- OA or APC mismatches
- article-type mismatches such as review journals for original research, method journals for non-method papers, data journals for non-resource papers, or very broad elite venues with high desk-reject risk
- whether ranking confidence is reduced because venue concepts are sparse or parsing looks suspicious

Keep the full ranked JSON for audit, debugging, or explicit broad-search requests. If the user asks for a wider net, rerun with a higher `--agent-top-n` or inspect the full ranked file directly.

7. Present the results in a concise decision-oriented format.

## Output requirements

Return:
- a Markdown table of the top 5 to 10 venues
- a short explanation for the top pick
- a three-step submission ladder:
  - stretch
  - target
  - safety

Recommended table columns:
- rank
- journal
- publisher
- fit
- risk
- impact proxy
- OA
- APC
- h-index

Also include:
- key caveats such as APC conflicts, weak topical fit, or unclear scope match
- the strategy used and any major risk reasons from the compact ranked summary
- the saved ranked-list path so later skills can reuse it
- the saved compact ranked-summary path when available

## Failure handling

- If parsing fails, report the failure and ask for a cleaner PDF or the original DOCX.
- If parsing succeeds but the abstract is implausibly long, sections are not split, or `reference_count` is unexpectedly zero, treat the parse as low-confidence and say so.
- If venue retrieval returns weak or irrelevant matches, refine the query concepts once and retry.
- If the manuscript looks CS-oriented and journal results dominate despite a conference preference, rerun with `--venue-types conference`.
- If conference acronyms such as `ICML`, `NeurIPS`, `KDD`, `SIGIR`, or `EMNLP` appear in the compact ranked summary, treat exact acronym alignment as useful scope evidence.
- If venue retrieval succeeds but venue concepts are sparse, continue with manual scope judgment and say the numeric ranking is low-confidence.
- If external data sources are unavailable, say so clearly and continue with whatever sources still work.
- If Elsevier metadata enrichment fails for some journals, continue with the remaining venue data and say that enrichment was partial.
- Do not fabricate journal policies, APC values, or indexing status.
- Do not pull the full ranked JSON into agent context unless the user explicitly wants a broader candidate set or the compact summary looks suspiciously thin.

## Handoff to other skills

- Use `journal-rules` after the user selects one or more target journals.
- Use `format-checker` after journal rules have been cached.

## Manual verification

Use these commands during local testing:

```bash
uv run --project scripts python -m sn_lib.parse "<path-to-manuscript>"
uv run --project scripts python -m sn_lib.venues "<query-string>" --per-page 10
uv run --project scripts python -m sn_lib.ranking --concepts <c1> <c2> <c3> --venues-json "<temp_dir>/sn_venues.json"
```
