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
        {"retrieved": True, "published_rank": 1},
        {"retrieved": True, "published_rank": 8},
        {"retrieved": False, "published_rank": None},
    ])
    assert metrics["retrieval_recall"] == 0.667
    assert metrics["ranked_recall"] == 0.667
    assert metrics["hit_at_1"] == 0.333
    assert metrics["hit_at_10"] == 0.667
    assert metrics["mrr"] == 0.375
