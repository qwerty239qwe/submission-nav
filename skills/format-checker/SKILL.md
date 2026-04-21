---
name: format-checker
description: Use when user wants to check whether a manuscript/figures/tables meet a target journal's rules. Compares manuscript metrics and figure properties to cached journal rules and flags violations.
---

# format-checker

## Preconditions
- Rules JSON for the journal(s) must exist in `<config-dir>/rules/`. If not, invoke `journal-rules` first.
- Manuscript parsed JSON available (else run `uv run --project scripts python -m sn_lib.parse <path>`).

## Steps

1. Confirm which journal to check against. If multiple rules files exist, ask user.

2. For each target journal:
   ```bash
   uv run --project scripts python -m sn_lib.figures "<pdf path>" \
     --rules-json <config-dir>/rules/<slug>.json \
     --word-count <N> > /tmp/sn_check_<slug>.json
   ```
   Where `<N>` is from the parsed manuscript JSON.

3. **Render report:**
   - Violations (must fix): red bullets.
   - Warnings (can't verify): yellow bullets.
   - OK: green bullets.

4. **Suggest fixes** inline: e.g. "Fig 2 is 150 dpi — re-export at 300 dpi (TIFF)." Keep suggestions specific; do not prescribe how to re-export unless asked.

5. **Non-PDF source:** if original manuscript is DOCX, figure DPI may be missing. Warn the user and recommend checking original image files manually.
