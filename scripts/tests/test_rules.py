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
    assert r.cache_status in {"fresh-fetch", "fresh-cache"}
    assert (tmp_config_dir / "rules" / "example-journal.json").exists()
    assert (tmp_config_dir / "cache" / "journal_rules" / "example-journal" / "raw.html").exists()


@respx.mock
def test_fetch_rules_uses_cached_copy_when_offline(tmp_config_dir):
    html = """<html><body><p>Manuscripts must not exceed 6000 words.</p></body></html>"""
    route = respx.get("https://journal.example/authors").mock(
        return_value=httpx.Response(200, text=html)
    )
    first = fetch_rules("Example Journal", "https://journal.example/authors")
    assert first.word_limit == 6000
    route.mock(side_effect=AssertionError("offline mode should not hit the network"))
    cached = fetch_rules("Example Journal", "https://journal.example/authors", offline=True)
    assert cached.word_limit == 6000
    assert cached.cache_status == "stale-cache"


@respx.mock
def test_fetch_rules_refreshes_when_requested(tmp_config_dir):
    route = respx.get("https://journal.example/authors").mock(
        side_effect=[
            httpx.Response(200, text="<html><body><p>Manuscripts must not exceed 6000 words.</p></body></html>"),
            httpx.Response(200, text="<html><body><p>Manuscripts must not exceed 7000 words.</p></body></html>"),
        ]
    )
    first = fetch_rules("Example Journal", "https://journal.example/authors")
    refreshed = fetch_rules("Example Journal", "https://journal.example/authors", refresh=True)
    assert first.word_limit == 6000
    assert refreshed.word_limit == 7000
    assert route.call_count == 2


@respx.mock
def test_fetch_rules_bypasses_http_cache_when_rules_cache_is_stale(tmp_config_dir):
    route = respx.get("https://journal.example/authors").mock(
        side_effect=[
            httpx.Response(200, text="<html><body><p>Manuscripts must not exceed 6000 words.</p></body></html>"),
            httpx.Response(200, text="<html><body><p>Manuscripts must not exceed 7000 words.</p></body></html>"),
        ]
    )
    first = fetch_rules("Example Journal", "https://journal.example/authors")
    refreshed = fetch_rules("Example Journal", "https://journal.example/authors", max_age_days=0)
    assert first.word_limit == 6000
    assert refreshed.word_limit == 7000
    assert refreshed.cache_status == "fresh-fetch"
    assert route.call_count == 2


def test_extract_rules_ignores_abstract_limit_as_word_limit(tmp_config_dir):
    html = """<html><body>
    <h3>Length</h3>
    <p>Manuscripts can be any length. There are no restrictions on word count.</p>
    <h3>Abstract</h3>
    <p>The Abstract should not exceed 300 words.</p>
    <p>Use Vancouver reference style.</p>
    </body></html>"""
    r = fetch_rules_from_html("PLOS ONE", "https://example.org", html)
    assert r.word_limit is None
    assert r.abstract_limit == 300
    assert r.reference_style == "vancouver"


def test_extract_rules_prefers_main_text_limit_over_figure_legend_limit(tmp_config_dir):
    html = """<html><body>
    <p>In most cases, we do not impose strict limits on word count or page number.</p>
    <li>The main text should be no more than 4,500 words.</li>
    <li>The title should be no more than 20 words.</li>
    <li>The abstract should be no more than 200 words.</li>
    <li>References (limited to 60 references, though not strictly enforced)</li>
    <p>Display items are limited to 8 figures and/or tables.</p>
    <p>Figure legends are limited to 350 words per figure.</p>
    <p>We use the standard Nature referencing style.</p>
    </body></html>"""
    r = fetch_rules_from_html("Scientific Reports", "https://example.org", html)
    assert r.word_limit == 4500
    assert r.abstract_limit == 200
    assert r.reference_limit == 60
    assert r.table_max == 8
    assert r.reference_style == "nature"


def test_extract_rules_handles_frontiers_reference_style_choice(tmp_config_dir):
    html = """<html><body>
    <p>Frontiers' journals use one of two reference styles, either Harvard (author-date) or Vancouver (numbered).</p>
    <p>Other examples may mention APA or Chicago in generic help text.</p>
    <p>Technical requirements for supplementary images: 300 DPI.</p>
    </body></html>"""
    r = fetch_rules_from_html("Frontiers in Immunology", "https://example.org", html)
    assert r.reference_style == "harvard/vancouver"
    assert r.figure_dpi == 300


def test_extract_rules_handles_free_reference_style(tmp_config_dir):
    html = """<html><body>
    <p>References may be submitted in any style or format, as long as it is consistent throughout the manuscript.</p>
    <p>Generic examples mention APA and Chicago.</p>
    </body></html>"""
    r = fetch_rules_from_html("iMeta", "https://example.org", html)
    assert r.reference_style == "free"


def test_extract_rules_handles_comma_separated_dpi(tmp_config_dir):
    html = """<html><body>
    <p>Line-art figures should be supplied at 1,200 DPI.</p>
    <p>Photographic images should be supplied at a minimum of 300 DPI.</p>
    </body></html>"""
    r = fetch_rules_from_html("Nature Communications", "https://example.org", html)
    assert r.figure_dpi == 300


def fetch_rules_from_html(journal: str, url: str, html: str) -> JournalRules:
    from sn_lib.rules import _extract_rules

    return _extract_rules(journal, url, html)
