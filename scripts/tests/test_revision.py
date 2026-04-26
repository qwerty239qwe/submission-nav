from sn_lib.revision import parse_reviewer_comments, build_response_skeleton

def test_parse_reviewer_comments_splits_items():
    raw = """Reviewer 1:
1. The methods section is unclear.
2. Figure 2 needs a scale bar.

Reviewer 2:
- Clarify novelty.
- Expand related work."""
    items = parse_reviewer_comments(raw)
    assert len(items) == 4
    assert items[0]["reviewer"] == "1"
    assert "methods" in items[0]["comment"].lower()
    assert items[2]["reviewer"] == "2"

def test_build_response_skeleton_structure():
    items = [{"reviewer": "1", "idx": 1, "comment": "Methods unclear."}]
    out = build_response_skeleton(items)
    assert "Reviewer 1" in out
    assert "Comment 1" in out
    assert "Response:" in out
    assert "Methods unclear." in out

def test_parse_reviewer_comments_falls_back_to_paragraphs():
    raw = """Reviewer 1:

The methods section is unclear and should explain the sampling procedure.

The discussion overstates the findings."""
    items = parse_reviewer_comments(raw)
    assert len(items) == 2
    assert items[0]["reviewer"] == "1"
    assert "sampling procedure" in items[0]["comment"].lower()
    assert "overstates the findings" in items[1]["comment"].lower()
