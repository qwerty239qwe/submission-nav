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

def test_parse_docx_prefers_plain_title_over_section_heading(tmp_path):
    p = tmp_path / "plain-title.docx"
    d = Document()
    d.add_paragraph("A Plain Title Without Title Style")
    d.add_paragraph("Alice Smith, Bob Jones")
    d.add_heading("Abstract", 1)
    d.add_paragraph("This abstract should not become the title.")
    d.save(str(p))
    m = parse_manuscript(p)
    assert m.title == "A Plain Title Without Title Style"
    assert m.authors == ["Alice Smith", "Bob Jones"]


def test_parse_docx_handles_numbered_headings_and_numbered_references(tmp_path):
    p = tmp_path / "numbered.docx"
    d = Document()
    d.add_paragraph("Interpretable Models for Mitochondrial Toxicity")
    d.add_paragraph("Alice Smith, Bob Jones")
    d.add_paragraph("1. Abstract")
    d.add_paragraph("This abstract should stay short.")
    d.add_paragraph("2. Materials and Methods")
    d.add_paragraph("Methods content.")
    d.add_paragraph("3. Results")
    d.add_paragraph("Results content.")
    d.add_paragraph("References")
    d.add_paragraph("1. Foo et al. 2020. https://doi.org/10.1000/foo")
    d.add_paragraph("2. Bar et al. 2021. https://doi.org/10.1000/bar")
    d.save(str(p))
    m = parse_manuscript(p)
    assert m.abstract == "This abstract should stay short."
    assert any("Materials and Methods" in s.heading for s in m.sections)
    assert any("Results" in s.heading for s in m.sections)
    assert m.reference_count == 2
