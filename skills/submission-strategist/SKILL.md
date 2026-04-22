---
name: submission-strategist
description: Use when the user wants journal or venue recommendations for a manuscript, asks where to submit, or provides a PDF or DOCX and wants ranked submission targets.
---

# submission-strategist

This skill helps an agent turn a manuscript into a ranked list of candidate journals.

It is designed to be usable from Codex, Claude, Gemini, or any other host that supports reusable skill instructions plus local command execution.

## When to use

Use this skill when the user:
- asks where a manuscript should be submitted
- wants a ranked list of journals or venues
- shares a manuscript file and wants fit, impact, or open-access tradeoff analysis

## Required inputs

- A manuscript path in PDF or DOCX format

## Optional inputs

- APC budget in USD
- Open-access-only preference
- journals to exclude
- preferred field, publisher, or impact range

If the manuscript path is missing, ask for it before proceeding.

## Preconditions

1. Ensure local helper dependencies are installed for the repository.
2. If API credentials are needed, run `sn-config` first.
3. Use a writable temp directory for intermediate JSON outputs.

## Procedure

1. Parse the manuscript:

```bash
uv run --project scripts python -m sn_lib.parse "<path-to-manuscript>" --out "<temp_dir>/sn_ms.json"
```

2. Read the parsed manuscript JSON and capture:
- title
- abstract
- section headings
- word count
- reference count

3. Derive 3 to 5 query concepts from the title and abstract.
- Prefer noun phrases or domain terms.
- Do not send the whole abstract as one query string.
- Build 2 to 4 short venue-search queries from the concepts, such as endpoint, method, domain, and application framing.
- If ranking signals are weak, broaden once toward journal-facing terms such as `computational toxicology`, `cheminformatics`, `bioinformatics`, or `drug safety`.

4. Retrieve candidate venues:

```bash
uv run --project scripts python -m sn_lib.venues "<query-string>" --per-page 40 --out "<temp_dir>/sn_venues.json"
```

5. Rank venues using the derived concepts:

```bash
uv run --project scripts python -m sn_lib.ranking --concepts <c1> <c2> <c3> --venues-json "<temp_dir>/sn_venues.json" [--apc-budget <usd>] --out "<temp_dir>/sn_ranked.json"
```

6. Review the ranked output and identify:
- strongest thematic fit
- best overall balance of fit and impact
- lower-risk fallback
- OA or APC mismatches
- whether ranking confidence is reduced because venue concepts are sparse or parsing looks suspicious

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
- impact proxy
- OA
- APC
- h-index

Also include:
- key caveats such as APC conflicts, weak topical fit, or unclear scope match
- the saved ranked-list path so later skills can reuse it

## Failure handling

- If parsing fails, report the failure and ask for a cleaner PDF or the original DOCX.
- If parsing succeeds but the abstract is implausibly long, sections are not split, or `reference_count` is unexpectedly zero, treat the parse as low-confidence and say so.
- If venue retrieval returns weak or irrelevant matches, refine the query concepts once and retry.
- If venue retrieval succeeds but venue concepts are sparse, continue with manual scope judgment and say the numeric ranking is low-confidence.
- If external data sources are unavailable, say so clearly and continue with whatever sources still work.
- Do not fabricate journal policies, APC values, or indexing status.

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
