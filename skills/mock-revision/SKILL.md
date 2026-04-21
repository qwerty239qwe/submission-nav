---
name: mock-revision
description: Use when user pastes reviewer comments or a decision letter and wants a point-by-point response letter draft. Parses comments, builds a response skeleton, and lets the model fill in substantive responses.
---

# mock-revision

## Inputs
- Reviewer comments (pasted text) or a path to a file containing them.

## Steps

1. Save comments to a temp file if pasted (`/tmp/sn_reviews.txt`).
2. Parse + build skeleton:
   ```bash
   uv run --project scripts python -m sn_lib.revision /tmp/sn_reviews.txt > /tmp/sn_rev.json
   ```
3. Read `skeleton` from the JSON. For each `[TODO: ...]` placeholder, draft a substantive response using the manuscript's content (re-parse manuscript if available). Cite section/line numbers.
4. Keep responses:
   - Concise (2–4 sentences).
   - Polite (thank the reviewer once per reviewer block).
   - Point to a concrete change in the manuscript OR justify not changing (with reasoning).
5. Output a complete Markdown response letter. Offer to save it to a path the user specifies.

## Boundaries
- Do NOT invent new experimental results or data.
- If a comment needs data the user hasn't provided, leave a `[NEED INPUT]` marker and list what's needed.
