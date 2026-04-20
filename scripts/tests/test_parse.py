from pathlib import Path
from docx import Document
from sn_lib.parse import parse_manuscript, Manuscript

def _make_docx(path: Path):
    d = Document()
    d.add_heading("A Novel Method for Widget Optimization", 0)
    d.add_paragraph("Alice Smith, Bob Jones")
    d.add_heading("Abstract", 1)
    d.add_paragraph("We present a new approach to widget optimization using gradient methods.")
    d.add_heading("Introduction", 1)
    d.add_paragraph("Widgets are important. Prior work ignored X.")
    d.add_heading("References", 1)
    d.add_paragraph("[1] Foo 2020. [2] Bar 2021.")
    d.save(str(path))

def test_parse_docx(tmp_path):
    p = tmp_path / "s.docx"
    _make_docx(p)
    m = parse_manuscript(p)
    assert isinstance(m, Manuscript)
    assert "Widget" in m.title
    assert m.abstract and "widget" in m.abstract.lower()
    assert any("Introduction" in s.heading for s in m.sections)
    assert m.word_count > 10
    assert m.reference_count >= 2
