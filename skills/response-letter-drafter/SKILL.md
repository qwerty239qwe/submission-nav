---
name: response-letter-drafter
description: Use after revision planning when the user wants a polished point-by-point response letter grounded in reviewer comments and author-prepared materials.
---

# response-letter-drafter

This skill drafts a response letter after the revision strategy is already understood and the authors have prepared enough material to support concrete answers.

It is intended for Codex, Claude, Gemini, and similar agent hosts that can combine reviewer comments with manuscript context and author notes.

## When to use

Use this skill when the user:
- wants a response letter draft
- has reviewer comments plus author notes or revised text
- has already triaged the comments and decided on a revision strategy

## Required inputs

- reviewer comments or structured review JSON
- author-prepared notes, revised text, or change summaries

## Optional inputs

- manuscript path
- revision plan from `review-revision-strategist`
- exact section or line references

## Recommended setup

1. If starting from raw reviewer comments, build the comment structure:

```bash
uv run --project scripts python -m sn_lib.revision "<path-to-review-comments>" > "<temp_dir>/sn_rev.json"
```

2. If manuscript context is needed, parse it:

```bash
uv run --project scripts python -m sn_lib.parse "<path-to-manuscript>" > "<temp_dir>/sn_ms.json"
```

3. If no revision strategy exists yet, run `review-revision-strategist` first.

## Procedure

1. Read the reviewer comments and group them by reviewer and comment number.
2. Read the author materials and map them to each comment.
3. Draft a response for each comment that:
- states what was changed, if anything
- points to the revised section, figure, table, or line when known
- explains the reasoning when the authors disagree
- stays professional and concise

4. If required evidence is missing:
- insert `[NEED INPUT]`
- state exactly what is needed

## Writing rules

- Thank each reviewer once per reviewer block
- Avoid repetitive gratitude in every item
- Keep responses concrete
- Prefer specific change descriptions over generic promises
- If the authors decline a request, justify it clearly and respectfully

## Output requirements

Return a complete Markdown response letter with:
- opening note to the editor and reviewers
- reviewer-by-reviewer organization
- point-by-point responses
- explicit markers for unresolved items

## Boundaries

- Do not invent new data, analyses, or textual changes
- Do not claim a revision was made unless supported by the provided materials
- If the authors have not supplied enough detail, stop short of overconfident prose and mark the gap clearly

## Handoff

After drafting, the user may want to:
- save the response letter to a file
- convert unresolved `[NEED INPUT]` items into an author checklist
