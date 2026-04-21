---
name: journal-rules
description: Use when user names target journals and asks for author guidelines, submission rules, word limits, figure requirements, or reference style. Fetches and summarizes journal author instructions; caches them locally.
---

# journal-rules

## Inputs
- One or more journal names. If user didn't name any, ask them to pick from the current ranked list (`/tmp/sn_ranked.json`) or type names directly.

## Steps

1. **Resolve author-guidelines URL per journal:**
   - Prefer user-supplied URL.
   - Else search OpenAlex for the journal's homepage (`host_organization`) and construct a likely author-guidelines URL, or ask the user to paste the link.
   - Do NOT guess URLs silently — confirm with the user before fetching.

2. **Fetch + extract:**
   ```bash
   uv run --project scripts python -m sn_lib.rules "<journal name>" "<guidelines url>" > <config-dir>/rules/<slug>.json
   ```

3. **Summarize per journal:** word limit, abstract limit, figure DPI, accepted figure formats, reference style, reference limit, plus 3–5 raw excerpts where extraction may be unreliable.

4. **Compare across journals:** if user gave 2+ journals, render a side-by-side table so they can see which is most restrictive.

## Output
- Structured JSON saved to cache.
- Human-readable summary in chat.
- If the page didn't yield values for a field, say "not detected" — do not hallucinate numbers.
