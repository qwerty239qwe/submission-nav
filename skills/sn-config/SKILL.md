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
- `elsevier_api_key`
- `doaj_key`

Elsevier note:
- `elsevier_api_key` is used for Elsevier Serial Title metadata enrichment
- local usage rules are documented in `api_rules/elsevier.md`
- do not use Elsevier credentials for broad or unnecessary request bursts

## Procedure

1. Show the current configuration:

```bash
uv run --project scripts python -m sn_lib.config show
```

2. Prefer writing secrets to the repo-local `.env` file.
- Use `.env.example` as the template for new users.
- Use config-file storage only if the user explicitly prefers it.

3. Ask the user which credentials they want to provide or update:
- Elsevier API key
- DOAJ API key

4. For each provided value, save it with:

```bash
uv run --project scripts python -m sn_lib.config set --key <key_name> --value "<value>"
```

Allowed `<key_name>` values:
- `elsevier_api_key`
- `doaj_key`

By default this writes to `.env`. To write to the local config JSON instead:

```bash
uv run --project scripts python -m sn_lib.config set --key <key_name> --value "<value>" --store config
```

5. Confirm the result by showing the config again:

```bash
uv run --project scripts python -m sn_lib.config show
```

## Environment-variable fallback

These environment variables can be used instead of persisted config:
- `ELSEVIER_API_KEY`
- `SCOPUS_KEY` for backward compatibility
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
- When using `elsevier_api_key`, follow `api_rules/elsevier.md` and keep requests limited to targeted metadata enrichment

## Manual verification

```bash
uv run --project scripts python -m sn_lib.config show
uv run --project scripts python -m sn_lib.config set --key elsevier_api_key --value "<value>"
uv run --project scripts python -m sn_lib.config set --key doaj_key --value "<value>"
```
