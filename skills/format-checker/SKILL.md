---
name: format-checker
description: Use when the user wants to check whether a manuscript, figures, or tables comply with a target journal's cached submission rules.
---

# format-checker

Check a manuscript against cached journal submission rules.

## Use When

- Manuscript readiness checks for a named journal.
- Figure, word-count, or rule-compliance checks.
- Must-fix formatting issues before submission.

## Inputs

- target journal name or slug
- manuscript path, preferably PDF for figure checks
- cached rules JSON from `journal-rules`

If rules are missing, run `journal-rules` first. Do not refetch author instructions during this skill unless the user asks.

## Procedure

1. Confirm the target journal and cached rules file.
2. Run the checker:

```bash
sn check "<manuscript-path>" --journal "<journal-slug>"
```

3. Read the generated check JSON from the manuscript run directory.
4. Classify findings into `Violations`, `Warnings`, and `OK`.
5. Give concrete fixes for each violation or warning.

## Report Format

- `Violations (must fix)`
- `Warnings (manual review or uncertain)`
- `OK`

For each item, state the rule, the observed issue, and the recommended fix.

## Reliability

- Do not claim compliance for unchecked constraints.
- If only a DOCX is available, say figure DPI may be unavailable.
- If rules are incomplete, list missing constraints.
