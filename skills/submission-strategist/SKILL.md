---
name: submission-strategist
description: Use when user wants to pick journals/venues for a manuscript, asks "where should I submit", or provides a PDF/DOCX asking for submission targets. Parses the manuscript, retrieves candidate venues, ranks them, and explains the best submission path.
---

# submission-strategist

## Inputs
- Path to manuscript (PDF or DOCX). Ask if not provided.
- Optional: APC budget USD, OA-only flag, exclude list.

## Steps

1. **Ensure config:** if `uv run --project scripts python -m sn_lib.config show` shows no `openalex_email`, invoke `sn-config` skill first.

2. **Parse manuscript:**
   ```bash
   uv run --project scripts python -m sn_lib.parse "<path>" > /tmp/sn_ms.json
   ```
   Read title, abstract, section headings, word count, reference count.

3. **Derive query concepts:** from title + abstract, extract 3–6 noun-phrase concepts. Use the abstract text as the free-text query string.

4. **Retrieve venues:**
   ```bash
   uv run --project scripts python -m sn_lib.venues "<query string>" --per-page 40 > /tmp/sn_venues.json
   ```

5. **Rank:**
   ```bash
   uv run --project scripts python -m sn_lib.ranking --concepts <c1> <c2> <c3> \
     --venues-json /tmp/sn_venues.json \
     [--apc-budget <N>] > /tmp/sn_ranked.json
   ```

6. **Present top 5–10:** table with columns: rank, journal, publisher, fit, impact_proxy, OA, APC, h-index. Then a short paragraph for the top pick explaining the rationale (fit + impact + OA fit + concerns).

7. **Recommend a submission ladder:** stretch (top by impact), target (top by combined score), safety (high fit, lower impact). Call out mismatches (e.g. OA-only manuscript but closed-access top pick).

## Output contract
- A markdown table + three-journal ladder + rationale.
- Persist ranked list path so follow-up skills (`journal-rules`, `format-checker`) can reuse it.
