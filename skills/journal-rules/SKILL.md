---
name: journal-rules
description: Use when the user names one or more target journals and wants author guidelines, submission rules, word limits, figure requirements, or reference-style constraints.
---

# journal-rules

This skill fetches and caches structured author-instruction rules for target journals.

## Inputs

Required:
- one or more journal names

Optional:
- direct author-guidelines URL
- saved local HTML file from a publisher page

If the journal is missing, ask the user to choose from the current ranked list or provide names directly.

## Procedure

1. Resolve the author-guidelines URL.
- Prefer a URL supplied by the user.
- If the URL is uncertain, say so before fetching.
- Do not silently invent a final author-guidelines URL.

2. Fetch and extract rules:

```bash
sn rules "<journal-name>" "<guidelines-url>"
```

For a saved HTML file:

```bash
sn rules "<journal-name>" --from-file "<page.html>"
```

Use `--refresh` only when the user asks for a fresh fetch or the cached result looks stale.

3. Read the saved JSON under the rules cache and summarize the detected fields.

## Output

For each journal, report:
- word limit
- abstract limit
- figure DPI requirements
- accepted figure formats
- reference style
- reference limit

If a value is missing, say `not detected`. If extraction is uncertain, say whether the value came from a heuristic extraction or a clearly labeled rule.

For multiple journals, return a compact comparison table focused on the most restrictive constraints.

## Handoff

Use `format-checker` after the target journal rules have been cached.
