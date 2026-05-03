from types import SimpleNamespace

from eval_submission_strategist import _expected_names, _metrics, _rank_of_expected


def _ranked(name, acronym=None):
    venue = SimpleNamespace(name=name, dblp_acronym=acronym)
    return SimpleNamespace(venue=venue)


def test_expected_names_accepts_aliases():
    names = _expected_names({
        "journal": "PLoS Computational Biology",
        "aliases": ["PLOS Computational Biology", "PLoS Comput Biol"],
    })
    assert "plos computational biology" in names
    assert "plos comput biol" in names


def test_rank_of_expected_matches_dblp_acronym():
    ranked = [
        _ranked("International Conference on Learning Representations", "ICLR"),
        _ranked("International Conference on Machine Learning", "ICML"),
    ]
    assert _rank_of_expected(ranked, ["icml"]) == 2


def test_metrics_separate_retrieval_and_ranking():
    metrics = _metrics([
        {
            "retrieved": True,
            "published_rank": 1,
            "top5_quality": {"rates": {"article_type_mismatch": 0.2, "high_risk": 0.0, "scope_caution": 0.0, "broad_megajournal": 0.0}, "has_contamination": True},
        },
        {
            "retrieved": True,
            "published_rank": 8,
            "top5_quality": {"rates": {"article_type_mismatch": 0.0, "high_risk": 0.2, "scope_caution": 0.2, "broad_megajournal": 0.0}, "has_contamination": True},
        },
        {
            "retrieved": False,
            "published_rank": None,
            "top5_quality": {"rates": {"article_type_mismatch": 0.0, "high_risk": 0.0, "scope_caution": 0.0, "broad_megajournal": 0.2}, "has_contamination": True},
        },
    ])
    assert metrics["retrieval_recall"] == 0.667
    assert metrics["ranked_recall"] == 0.667
    assert metrics["hit_at_1"] == 0.333
    assert metrics["hit_at_10"] == 0.667
    assert metrics["mrr"] == 0.375
    assert metrics["top5_article_type_mismatch_rate"] == 0.067
    assert metrics["top5_high_risk_rate"] == 0.067
    assert metrics["top5_scope_caution_rate"] == 0.067
    assert metrics["top5_broad_megajournal_rate"] == 0.067
    assert metrics["top5_contaminated_case_rate"] == 1.0
