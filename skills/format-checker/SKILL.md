---
name: format-checker
description: Use when the user wants to check whether a manuscript, figures, or tables comply with a target journal's cached submission rules.
---

# format-checker

This skill compares manuscript and figure properties against cached journal rules and reports likely violations.

It is suitable for Codex, Claude, Gemini, and similar agent hosts that can run local helper commands.

## When to use

Use this skill when the user:
- wants a pre-submission format check
- asks whether a manuscript meets a journal's figure or text constraints
- wants a list of must-fix formatting issues before submission

## Preconditions

Before running this skill:

1. A rules JSON file must exist under the submission-nav rules cache.
- If not, run `journal-rules` first.

2. A parsed manuscript JSON or a manuscript source file must be available
- If not, run:

```bash
sn parse "<path-to-manuscript>"
```

## Required inputs

- target journal
- manuscript PDF path for figure inspection

## Optional inputs

- parsed manuscript JSON with word count
- original DOCX path for supplemental text checks

## Procedure

1. Confirm which journal rules file should be used.
- If multiple cached rules files exist, ask the user to choose.

2. Let the helper parse the manuscript and determine word count.

3. Run the figure and format check:

```bash
sn check "<pdf-path>" --journal "<slug>"
```

4. Read the generated JSON and classify results into:
- violations
- warnings
- passes

5. Report findings with concrete next actions.

## Output requirements

Present:
- `Violations (must fix)`
- `Warnings (could not verify or may need manual review)`
- `OK`

For each violation or warning, include a specific fix suggestion when possible.

Examples:
- `Figure 2 is below the required DPI threshold; re-export at the journal minimum DPI.`
- `Reference limit not detected automatically; verify against the source document manually.`

## Reliability rules

- If the manuscript source is DOCX and only the PDF is inspected, warn that original image DPI may be unavailable
- Do not claim compliance for fields that were not actually checked
- If the rules JSON is incomplete, say which constraints could not be evaluated

## Handoff

If missing rules block the check, run `journal-rules` first and then retry.

## Manual verification

```bash
sn check "<pdf-path>" --journal "<slug>"
```
