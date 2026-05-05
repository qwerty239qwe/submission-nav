from datetime import date

import httpx
import respx

import json

from eval_public_crossfield import default_from_date, default_to_date, fetch_candidates, _matches_field, summarize_results, summarize_run


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


@respx.mock
def test_fetch_candidates_raises_on_openalex_timeout():
    respx.get("https://api.openalex.org/works").mock(side_effect=httpx.ReadTimeout("timed out"))

    try:
        fetch_candidates("widget science", from_date="2021-01-01", to_date="2026-04-30")
    except RuntimeError as exc:
        assert "ReadTimeout" in str(exc)
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


def test_summarize_run_reports_best_fit_and_bucketed_ranks(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "ranked_agent_balanced.json").write_text(json.dumps({
        "best_fit_ranked": [
            {"journal": "Expected Journal", "score": 0.8, "rationale": {}},
            {"journal": "Other Journal", "score": 0.7, "rationale": {}},
        ],
        "risk_adjusted_recommendations": [
            {"journal": "Other Journal", "score": 0.7, "rationale": {}},
        ],
        "counts": {"target": 1},
    }), encoding="utf-8")
    (run_dir / "ranked_balanced.json").write_text("[]", encoding="utf-8")
    (run_dir / "contribution_assessment.json").write_text(json.dumps({
        "contribution_tier": "exploratory",
        "ambition_band": "safe_specialty",
    }), encoding="utf-8")
    work = {
        "title": "Example",
        "publication_year": 2024,
        "publication_date": "2024-01-01",
        "primary_location": {
            "source": {
                "display_name": "Expected Journal",
                "summary_stats": {"2yr_mean_citedness": 2.0},
            }
        },
    }
    result = summarize_run(run_dir, work, "chemistry", "middle", 1.23, 0, "")
    assert result["published_venue_in_top10"] is True
    assert result["published_best_fit_rank"] == 1
    assert result["published_candidate_present"] is False
    assert result["published_bucketed_rank"] is None
    assert result["top_recommendations"] == ["Expected Journal", "Other Journal"]
    assert result["bucketed_recommendations"] == ["Other Journal"]


def test_summarize_results_reports_separate_primary_metrics():
    summary = summarize_results([
        {
            "returncode": 0,
            "published_best_fit_rank": 3,
            "published_bucketed_rank": None,
            "published_full_rank": 3,
            "published_candidate_present": True,
            "top5_quality": {"rates": {"scope_caution": 0.2}, "has_contamination": True},
        },
        {
            "returncode": 0,
            "published_best_fit_rank": None,
            "published_bucketed_rank": 8,
            "published_full_rank": 18,
            "published_candidate_present": True,
            "top5_quality": {"rates": {"scope_caution": 0.0}, "has_contamination": False},
        },
    ])
    assert summary["best_fit_top10"] == 0.5
    assert summary["bucketed_top10"] == 0.5
    assert summary["candidate_present"] == 1.0
    assert summary["full_rank_top20"] == 1.0
    assert summary["top5_contaminated_case_rate"] == 0.5
