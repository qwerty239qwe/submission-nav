from pathlib import Path
from docx import Document
from sn_lib.parse import parse_manuscript, Manuscript, _pick_pdf_title_and_authors, _pick_pdf_title_from_layout

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
    assert len(m.references) == 2
    assert "10.1000/foo" in m.references[0]


def test_parse_summary_dict_is_compact(tmp_path):
    p = tmp_path / "summary.docx"
    _make_docx(p)
    m = parse_manuscript(p)
    summary = m.to_summary_dict()
    assert summary["title"] == m.title
    assert "section_headings" in summary
    assert "sections" not in summary
    assert summary["reference_count"] == m.reference_count


def test_pick_pdf_title_and_authors_handles_plos_style_front_matter():
    lines = [
        "RESEARCH ARTICLE",
        "Galaxy-ML: An accessible, reproducible, and",
        "scalable machine learning toolkit for biomedicine",
        "Qiang Gu1,2, Anup Kumar3, Simon Bray3",
        "Department of Biomedical Engineering, Oregon Health & Science University",
        "Abstract",
    ]
    title, authors = _pick_pdf_title_and_authors(lines)
    assert title == "Galaxy-ML: An accessible, reproducible, and scalable machine learning toolkit for biomedicine"
    assert authors == ["Qiang Gu1,2, Anup Kumar3, Simon Bray3"]


def test_pick_pdf_title_from_layout_skips_journal_and_article_labels():
    rows = [
        (31.4, 25.0, "Scientific Reports"),
        (48.9, 9.0, "https://doi.org/10.1038/example"),
        (66.5, 21.0, "Article in Press"),
        (114.5, 28.0, "Protium heptaphyllum, a tree native"),
        (145.3, 28.0, "to the Atlantic Forest, is a potential source"),
        (175.3, 28.0, "of compounds against important cocoa"),
        (205.3, 28.0, "phytopathogen"),
    ]
    assert _pick_pdf_title_from_layout(rows) == (
        "Protium heptaphyllum, a tree native to the Atlantic Forest, is a potential source "
        "of compounds against important cocoa phytopathogen"
    )


def test_pick_pdf_title_from_layout_handles_interleaved_sidebar_metadata():
    rows = [
        (50.4, 7.0, "TYPE Original Research"),
        (136.9, 21.0, "The protective effect of"),
        (176.8, 7.0, "OPEN ACCESS"),
        (186.9, 21.0, "probiotics on intestinal"),
        (192.4, 5.5, "EDITED BY"),
        (211.9, 21.0, "mucosal injury and dysbiosis"),
        (236.9, 21.0, "in infants with congenital"),
        (261.9, 21.0, "heart disease undergoing"),
        (300.4, 11.0, "Zhixuan Zhang 1"),
    ]
    assert _pick_pdf_title_from_layout(rows) == (
        "The protective effect of probiotics on intestinal mucosal injury and dysbiosis "
        "in infants with congenital heart disease undergoing"
    )
