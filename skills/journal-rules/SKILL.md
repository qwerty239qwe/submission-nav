---
name: journal-rules
description: Use when the user names one or more target journals and wants author guidelines, submission rules, word limits, figure requirements, or reference-style constraints.
---

# journal-rules

This skill fetches and summarizes author-instruction pages for target journals, then caches structured rule data locally.

It is written to work across agent hosts that support reusable skill instructions and local command execution.

## When to use

Use this skill when the user:
- asks for author guidelines for a journal
- wants word or abstract limits
- wants figure, file-format, or reference-style requirements
- wants to compare submission constraints across multiple journals

## Required inputs

- one or more journal names

## Optional inputs

- direct author-guidelines URLs supplied by the user

If the user did not name a journal:
- ask them to choose from the current ranked list, if available
- otherwise ask them to provide journal names directly

## Procedure

1. Resolve an author-guidelines URL for each journal.
- Prefer a URL supplied by the user.
- Otherwise, look up a likely journal homepage or metadata source.
- Do not silently guess a final author-guidelines URL. Confirm it with the user before fetching if the URL is uncertain.

2. Fetch and extract structured rules:

```bash
uv run --project scripts python -m sn_lib.rules "<journal-name>" "<guidelines-url>" > "<config_dir>/rules/<slug>.json"
```

3. Read the saved JSON and summarize the fields most relevant to manuscript preparation.

4. If the user supplied multiple journals, compare them side by side.

## Output requirements

For each journal, report:
- word limit
- abstract limit
- figure DPI requirements
- accepted figure formats
- reference style
- reference limit

If extraction is uncertain, include a small number of raw excerpts or direct notes from the fetched content.

If the user asked about multiple journals, return a comparison table highlighting the most restrictive requirements.

## Reliability rules

- If a field is missing, say `not detected`
- Do not hallucinate numeric limits
- Make clear when a value came from heuristic extraction rather than a clearly labeled rule on the source page

## Caching

- Save each journal's structured rules JSON under `<config_dir>/rules/`
- Reuse cached rule files when appropriate, but refresh them if the user asks or if the existing data looks stale

## Handoff to other skills

Use `format-checker` after rules have been cached and the target journal is known.

## Manual verification

```bash
uv run --project scripts python -m sn_lib.rules "<journal-name>" "<guidelines-url>"
```
