---
name: sn-config
description: Use on first setup or when the user wants to add or change API credentials for submission-nav.
---

# sn-config

This skill manages local configuration for helper APIs used by submission-nav.

## Supported Keys

- `elsevier_api_key`
- `doaj_key`
- `openalex_email`
- `crossref_email`

`elsevier_api_key` is used only for targeted Elsevier Serial Title metadata enrichment. Follow `api_rules/elsevier.md` and avoid broad request bursts.

## Procedure

1. Show current configuration:

```bash
sn config show
```

2. Prefer writing secrets to the repo-local `.env` file. Use `.env.example` as the template for new users.

3. Save provided values:

```bash
sn config set --key elsevier_api_key --value "<value>"
sn config set --key doaj_key --value "<value>"
sn config set --key openalex_email --value "name@example.org"
sn config set --key crossref_email --value "name@example.org"
```

By default this writes to `.env`. If the user explicitly prefers config JSON:

```bash
sn config set --key <key_name> --value "<value>" --store config
```

4. Confirm with:

```bash
sn config show
```

## Safety

- Never echo full secrets back to the user after saving them.
- Mask secrets in user-facing output.
- Never write secrets into skill docs, tests, README examples, or commits.
- If optional credentials are missing, continue and state which downstream enrichment may be limited.
