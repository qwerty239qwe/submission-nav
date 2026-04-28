---
name: submission-nav
description: Journal and conference venue targeting from a manuscript, plus downstream submission and revision workflows (author rules, format checks, revision planning, reviewer triage, response letters).
---

# submission-nav

Use this as the npx-installable entry point for the submission-nav toolkit. The directory containing this file is `SN_HOME`; resolve bundled commands relative to it, not the user's current project.

## Command Surface

Prefer the canonical CLI:

```bash
# Windows
"<SN_HOME>/bin/sn.cmd" doctor

# macOS / Linux
"<SN_HOME>/bin/sn" doctor
```

If `sn` is already on `PATH`, use `sn <command>` directly. Key commands are:

- `sn strategist <manuscript>` for ranked journal or conference recommendations
- `sn rules <journal> <url>` for cached author-instruction extraction
- `sn check <manuscript> --journal <slug>` for format checks against cached rules
- `sn parse <manuscript>` and `sn concepts <manuscript>` for reusable manuscript metadata
- `sn triage <comments-file>` for structured reviewer-comment triage
- `sn config show|set` for local credentials
- `sn runs ls|path|clean` for cached workflow outputs

For API credentials, use `sn-config` or edit the repo-local `.env` from `<SN_HOME>/.env.example`. Never print secrets.

## Workflows

Use the specialized workflow files under `<SN_HOME>/skills/`:

- Journal or venue recommendations: `skills/submission-strategist/SKILL.md`
- Journal author instructions and cached rules: `skills/journal-rules/SKILL.md`
- Format checks: `skills/format-checker/SKILL.md`
- Pre-submission revision planning: `skills/pre-submission-revision/SKILL.md`
- Reviewer-comment triage: `skills/review-revision-strategist/SKILL.md`
- Response-letter drafting: `skills/response-letter-drafter/SKILL.md`
- Credential setup: `skills/sn-config/SKILL.md`

## Output Rules

- Keep generated working files in the run cache or a user-provided temp directory, not inside `SN_HOME`.
- Reuse cached run outputs and cached journal rules when appropriate; use `--force` or `--refresh` only when the user asks for a fresh run.
- Do not fabricate journal limits, APCs, indexing status, or author-rule details.
- For venue recommendations, report the strategy used and keep raw score/risk reasons available for audit.
