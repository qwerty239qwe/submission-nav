---
name: submission-nav
description: Academic submission navigation toolkit for manuscript journal or venue targeting, journal author-rule fetching, format checking, pre-submission revision planning, review-response strategy, and response-letter drafting. Use when a user wants submission recommendations, journal guidelines, manuscript compliance checks, or submission/revision workflow support.
---

# submission-nav

Use this skill as the npx-installable, self-contained entry point for the submission-nav toolkit.

The directory containing this `SKILL.md` is `SN_HOME`. Resolve all bundled helper commands relative to `SN_HOME`, not the user's current project directory.

## Setup Check

Before running helper commands:

```bash
uv run --project "<SN_HOME>/scripts" python -m sn_lib.config show
```

If dependencies are missing, run the bundled setup script:

```bash
# Windows
powershell -ExecutionPolicy Bypass -File "<SN_HOME>/bin/install.ps1"

# macOS / Linux
bash "<SN_HOME>/bin/install.sh"
```

For API credentials, use the `sn-config` workflow or edit the repo-local `.env` based on `<SN_HOME>/.env.example`. Do not print secrets.

## Workflows

Use the specialized workflow files under `<SN_HOME>/skills/`:

- Journal or venue recommendations: read `<SN_HOME>/skills/submission-strategist/SKILL.md`
- Journal author instructions and cached rules: read `<SN_HOME>/skills/journal-rules/SKILL.md`
- Format checks against cached journal rules: read `<SN_HOME>/skills/format-checker/SKILL.md`
- Pre-submission revision planning: read `<SN_HOME>/skills/pre-submission-revision/SKILL.md`
- Reviewer-comment triage: read `<SN_HOME>/skills/review-revision-strategist/SKILL.md`
- Response-letter drafting: read `<SN_HOME>/skills/response-letter-drafter/SKILL.md`
- Credential setup: read `<SN_HOME>/skills/sn-config/SKILL.md`

When those workflow files show commands using `scripts`, rewrite them to use `<SN_HOME>/scripts`.

Example:

```bash
uv run --project "<SN_HOME>/scripts" python -m sn_lib.parse "<manuscript>" --out "<tmp>/ms_full.json" --summary-out "<tmp>/ms_summary.json"
```

## Output Rules

- Keep generated working files in a user-provided directory or a temp directory, not inside `SN_HOME`.
- Use cached journal rules when available and say when live publisher pages are blocked.
- Do not fabricate journal limits, APCs, indexing status, or author-rule details.
- For venue recommendations, report the strategy used and keep raw score/risk reasons available for audit.
