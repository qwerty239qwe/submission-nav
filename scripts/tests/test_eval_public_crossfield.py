from datetime import date

import httpx
import respx

from eval_public_crossfield import default_from_date, default_to_date, fetch_candidates, _matches_field


def test_default_from_date_uses_five_year_window():
    assert default_from_date(date(2026, 4, 30)) == "2021-01-01"


def test_default_to_date_uses_today():
    assert default_to_date(date(2026, 4, 30)) == "2026-04-30"


@respx.mock
def test_fetch_candidates_applies_publication_window():
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    assert fetch_candidates("widget science", from_date="2021-04-30", to_date="2026-04-30") == []

    params = route.calls[0].request.url.params
    assert params["filter"] == (
        "type:article,has_abstract:true,primary_location.source.type:journal,"
        "from_publication_date:2021-04-30,to_publication_date:2026-04-30"
    )


@respx.mock
def test_fetch_candidates_raises_on_openalex_error():
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(429, json={"message": "Rate limit exceeded"})
    )

    try:
        fetch_candidates("widget science", from_date="2021-01-01", to_date="2026-04-30")
    except RuntimeError as exc:
        assert "HTTP 429" in str(exc)
        assert "Rate limit exceeded" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_matches_field_prefers_openalex_topic_metadata_when_available():
    work = {
        "title": "Machine learning for molecular synthesis",
        "abstract_inverted_index": {"machine": [0], "learning": [1], "molecule": [2]},
        "primary_topic": {
            "display_name": "Chemical synthesis",
            "field": {"display_name": "Chemistry"},
            "domain": {"display_name": "Physical sciences"},
        },
    }

    assert _matches_field(work, "chemistry") is True
    assert _matches_field(work, "computer_science") is False


def test_matches_field_falls_back_to_text_without_topics():
    work = {
        "title": "Machine learning algorithm for neural network optimization",
        "abstract_inverted_index": None,
    }

    assert _matches_field(work, "computer_science") is True
