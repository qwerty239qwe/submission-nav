---
name: sn-config
description: Use when first using submission-navigator or when user says "set my API keys", "configure submission navigator", or mentions missing OpenAlex/Crossref/Scopus/DOAJ keys. Stores credentials in ~/.submission-navigator/config.json.
---

# submission-navigator config

## When to run
- First invocation of any submission-navigator skill.
- User asks to add/change API credentials.

## Steps
1. Show current config:
   ```bash
   uv run --project scripts python -m sn_lib.config show
   ```
2. Ask the user (one message, bulleted) whether they want to provide each of:
   - OpenAlex email (recommended, no key — just email for polite pool)
   - Crossref email
   - Scopus API key (optional)
   - DOAJ API key (optional)
3. For each value the user provides, run:
   ```bash
   uv run --project scripts python -m sn_lib.config set --key <key_name> --value "<value>"
   ```
   where `<key_name>` is one of `openalex_email`, `crossref_email`, `scopus_key`, `doaj_key`.
4. Confirm by re-running `uv run --project scripts python -m sn_lib.config show`.

## Notes
- Never echo secret keys back in plain text after saving. Show only `***` + last 4 chars.
- If user skips a key, continue — downstream skills degrade gracefully.
