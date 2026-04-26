from __future__ import annotations
import re

_REVIEWER_HEAD = re.compile(r"^\s*Reviewer\s+(\d+)\s*[:\-]?\s*$", re.I | re.M)
_ITEM = re.compile(r"^\s*(?:(\d+)[.)]|[-*\u2022])\s+(.*)$", re.M)

def parse_reviewer_comments(text: str) -> list[dict]:
    blocks: list[tuple[str, str]] = []
    positions = [(m.start(), m.group(1)) for m in _REVIEWER_HEAD.finditer(text)]
    if not positions:
        positions = [(0, "1")]
    for i, (pos, rev) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        blocks.append((rev, text[pos:end]))
    items: list[dict] = []
    for rev, blk in blocks:
        block_items = list(_ITEM.finditer(blk))
        for i, m in enumerate(block_items, start=1):
            idx = int(m.group(1)) if m.group(1) else i
            items.append({"reviewer": rev, "idx": idx, "comment": m.group(2).strip()})
        if block_items:
            continue
        paragraphs = []
        for part in re.split(r"\n\s*\n+", blk):
            lines = [line.strip() for line in part.splitlines()]
            para = " ".join(line for line in lines if line and not _REVIEWER_HEAD.match(line))
            if para:
                paragraphs.append(para)
        for i, para in enumerate(paragraphs, start=1):
            items.append({"reviewer": rev, "idx": i, "comment": para})
    return items

def build_response_skeleton(items: list[dict]) -> str:
    lines: list[str] = ["# Response to Reviewers", ""]
    by_rev: dict[str, list[dict]] = {}
    for it in items:
        by_rev.setdefault(it["reviewer"], []).append(it)
    for rev in sorted(by_rev):
        lines.append(f"## Reviewer {rev}")
        lines.append("")
        for it in by_rev[rev]:
            lines.append(f"### Comment {it['idx']}")
            lines.append(f"> {it['comment']}")
            lines.append("")
            lines.append("**Response:** [TODO: address the comment; cite revised section/line.]")
            lines.append("")
            lines.append("**Changes in manuscript:** [TODO: quote new/changed text.]")
            lines.append("")
    return "\n".join(lines)

def _main():
    import argparse, json, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("comments_file")
    args = ap.parse_args()
    text = open(args.comments_file, encoding="utf-8").read()
    items = parse_reviewer_comments(text)
    skeleton = build_response_skeleton(items)
    print(json.dumps({"items": items, "skeleton": skeleton}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
