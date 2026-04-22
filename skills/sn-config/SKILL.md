---
name: sn-config
description: Use on first setup or when the user wants to add or change API credentials for submission-nav.
---

# sn-config

This skill manages local configuration for helper APIs used by the submission-nav tools.

It is intended for any agent host that can follow skill instructions and run local commands.

## When to use

Use this skill when:
- the user is setting up submission-nav for the first time
- a downstream command reports missing credentials
- the user wants to add, replace, or inspect saved API keys

## Scope

This skill stores only configuration values needed by the helper library.

Supported config keys:
- `scopus_key`
- `doaj_key`

## Procedure

1. Show the current configuration:

```bash
uv run --project scripts python -m sn_lib.config show
```

2. Ask the user which credentials they want to provide or update:
- Scopus API key
- DOAJ API key

3. For each provided value, save it with:

```bash
uv run --project scripts python -m sn_lib.config set --key <key_name> --value "<value>"
```

Allowed `<key_name>` values:
- `scopus_key`
- `doaj_key`

4. Confirm the result by showing the config again:

```bash
uv run --project scripts python -m sn_lib.config show
```

## Environment-variable fallback

These environment variables can be used instead of persisted config:
- `SCOPUS_KEY`
- `DOAJ_KEY`
- `OPENALEX_EMAIL`
- `OPENALEX_MAILTO`
- `CROSSREF_EMAIL`

If a `.env` file exists at the repository root, treat those values as valid fallbacks when supported by the helper library.

## Output requirements

- Confirm which keys are configured
- Mask secrets in any user-facing output
- Show only masked values such as `***abcd`

## Safety rules

- Never echo full secrets back to the user after saving them
- Never write secrets into skill documentation, test fixtures, or example commands
- If the user skips optional credentials, continue and note that some downstream features may degrade gracefully

## Manual verification

```bash
uv run --project scripts python -m sn_lib.config show
uv run --project scripts python -m sn_lib.config set --key scopus_key --value "<value>"
uv run --project scripts python -m sn_lib.config set --key doaj_key --value "<value>"
```
