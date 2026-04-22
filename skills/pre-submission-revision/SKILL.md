---
name: pre-submission-revision
description: Use before submission or resubmission to identify likely reviewer concerns, tighten the manuscript, and generate a prioritized revision plan.
---

# pre-submission-revision

This skill reviews a manuscript before submission and produces a practical revision plan aimed at reducing preventable reviewer objections.

It is intended for Codex, Claude, Gemini, and similar agent hosts that can follow reusable instructions and inspect manuscript files.

## When to use

Use this skill when the user:
- wants a manuscript reviewed before journal submission
- asks what should be improved before submission
- wants likely reviewer objections surfaced in advance
- wants a prioritized revision checklist before resubmission

## Required inputs

- manuscript path in PDF or DOCX format

## Optional inputs

- target journal
- target audience or field
- specific author concerns
- ranked journal list from `submission-strategist`
- journal rules from `journal-rules`

## Recommended setup

1. Parse the manuscript:

```bash
uv run --project scripts python -m sn_lib.parse "<path-to-manuscript>" > "<temp_dir>/sn_ms.json"
```

2. If the target journal is known, use `journal-rules` first.
3. If venue selection is still open, use `submission-strategist` first.

## Procedure

1. Read the manuscript structure, abstract, section headings, and overall length.
2. Assess likely weaknesses in:
- title and abstract clarity
- framing and novelty positioning
- method transparency
- result presentation
- discussion discipline
- limitation handling
- figure and table communication
- reference coverage

3. If a target journal is known, align the critique to that journal's likely expectations and cached rules.
4. Distinguish between:
- must-fix issues before submission
- worthwhile improvements if time allows
- optional polish items

5. Anticipate likely reviewer comments and convert them into revision actions.

## Output requirements

Return:
- a short readiness assessment
- a prioritized revision list
- likely reviewer objections
- a section-by-section action plan

Recommended structure:
- `Critical before submission`
- `Strong improvements`
- `Optional polish`
- `Likely reviewer objections`

Each action item should include:
- issue
- why it matters
- where to revise
- suggested strategy

## Boundaries

- Do not invent missing experiments or data
- Do not assume journal-specific requirements unless the journal is known
- If a concern depends on missing context, say so explicitly

## Handoff

- Use `review-revision-strategist` after reviewer comments arrive.
- Use `response-letter-drafter` only after the authors have prepared revision notes or manuscript changes.
