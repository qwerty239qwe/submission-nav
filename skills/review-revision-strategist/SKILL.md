---
name: review-revision-strategist
description: Use when reviewer comments or a decision letter arrive and the user needs a triaged revision plan, comment prioritization, and response strategy before drafting the letter.
---

# review-revision-strategist

This skill organizes reviewer feedback into a revision strategy. It is for planning, triage, and effort allocation, not final response-letter prose.

It is suitable for Codex, Claude, Gemini, and similar agent hosts that can inspect comments, manuscripts, and supporting notes.

## When to use

Use this skill when the user:
- has reviewer comments or a decision letter
- wants to know which comments deserve major effort
- wants to plan a revision before drafting the response letter
- wants to identify which comments should be accepted, partially addressed, or rebutted

## Required inputs

One or more of:
- pasted reviewer comments
- decision letter text
- path to a comments file

## Optional inputs

- manuscript path
- author notes
- lab meeting notes
- proposed new analyses
- journal decision type such as minor revision, major revision, or reject and resubmit

## Recommended setup

1. If comments are pasted inline, save them to a temp file:

`<temp_dir>/sn_reviews.txt`

2. Build the structured comment list:

```bash
sn triage "<temp_dir>/sn_reviews.txt"
```

3. If manuscript context is available, parse it:

```bash
sn parse "<path-to-manuscript>"
```

## Procedure

1. Group reviewer comments by theme, not just by reviewer number.
Possible themes:
- novelty and significance
- methods and reproducibility
- statistics and analysis
- figures and presentation
- interpretation and claims
- literature coverage
- formatting or compliance

2. For each comment, assign a strategy label:
- `accept and revise`
- `partially revise`
- `clarify without major text changes`
- `rebut with justification`
- `needs author input`

3. For each comment, estimate:
- priority
- likely effort
- manuscript sections affected
- evidence or materials needed
- risk if handled poorly

4. Identify comments that are:
- easy wins
- high-impact scientific issues
- likely based on misunderstanding
- not worth disproportionate effort

5. Produce a revision plan that helps the authors decide what to do before any response letter is drafted.

## Output requirements

Return:
- a brief top-level strategy summary
- a triage table of reviewer comments
- a prioritized to-do list for the authors
- a materials checklist for response drafting

Recommended table columns:
- reviewer
- comment
- theme
- priority
- effort
- strategy
- manuscript sections
- author materials needed

## Boundaries

- Do not draft the full response letter here except for short example phrasings
- Do not assume every reviewer request should be fully implemented
- Do not invent experiments, analyses, or manuscript changes

## Handoff

Use `response-letter-drafter` after the authors provide:
- revision notes
- manuscript changes
- analysis outputs
- replacement text
