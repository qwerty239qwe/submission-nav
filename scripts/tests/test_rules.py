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
