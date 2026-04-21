import respx, httpx
from sn_lib.rules import fetch_rules, JournalRules

@respx.mock
def test_fetch_rules_from_homepage(tmp_config_dir):
    html = """<html><body>
    <h1>Author Guidelines</h1>
    <p>Manuscripts must not exceed 6000 words.</p>
    <p>Figures should be at least 300 dpi and in TIFF or EPS format.</p>
    <p>Use Vancouver reference style.</p>
    </body></html>"""
    respx.get("https://journal.example/authors").mock(
        return_value=httpx.Response(200, text=html)
    )
    r = fetch_rules("Example Journal", "https://journal.example/authors")
    assert isinstance(r, JournalRules)
    assert r.word_limit == 6000
    assert r.figure_dpi == 300
    assert "TIFF" in r.figure_formats or "EPS" in r.figure_formats
    assert "vancouver" in r.reference_style.lower()
