from sn_lib.venues import VenueHit
from sn_lib.ranking import rank_venues, summarize_ranked

def _v(name, concepts, impact, oa=False, apc=None):
    return VenueHit(id=name, name=name, issn=None, publisher=None,
                    is_oa=oa, apc_usd=apc, impact_proxy=impact,
                    h_index=None, concepts=concepts, source="openalex")

def test_fit_dominates_when_equal_impact():
    ms_concepts = ["widget optimization", "gradient methods"]
    v1 = _v("Good", ["widget optimization", "optimization"], 2.0)
    v2 = _v("Bad", ["astronomy", "cosmology"], 2.0)
    ranked = rank_venues(ms_concepts, [v1, v2])
    assert ranked[0].venue.name == "Good"
    assert ranked[0].score > ranked[1].score
    assert ranked[0].rationale["fit"] > ranked[1].rationale["fit"]

def test_impact_tiebreaks_when_fit_equal():
    v1 = _v("Hi", ["x"], 5.0)
    v2 = _v("Lo", ["x"], 1.0)
    ranked = rank_venues(["x"], [v1, v2])
    assert ranked[0].venue.name == "Hi"

def test_apc_penalty_when_budget_set():
    v1 = _v("Free", ["x"], 3.0, oa=True, apc=0)
    v2 = _v("Pricey", ["x"], 3.0, oa=True, apc=5000)
    ranked = rank_venues(["x"], [v1, v2], apc_budget_usd=1000)
    assert ranked[0].venue.name == "Free"


def test_title_fallback_when_concepts_missing():
    v1 = _v("Computational Toxicology", [], 2.0)
    v2 = _v("Journal of Botany", [], 2.0)
    ranked = rank_venues(["computational toxicology"], [v2, v1])
    assert ranked[0].venue.name == "Computational Toxicology"


def test_summarize_ranked_limits_tail_and_concepts():
    venues = [
        _v("Computational Toxicology", ["a", "b", "c", "d"], 3.0),
        _v("Journal of Botany", ["x", "y"], 1.0),
    ]
    ranked = rank_venues(["computational toxicology"], venues)
    summary = summarize_ranked(ranked, top_n=1, concept_limit=2)
    assert len(summary) == 1
    assert summary[0]["journal"] == "Computational Toxicology"
    assert summary[0]["top_concepts"] == ["a", "b"]


def test_broad_journal_prestige_does_not_beat_scope_by_default():
    broad = _v("Cell", ["cancer research"], 25.0)
    specific = _v("BMC Bioinformatics", ["machine learning", "biomedicine", "toolkit"], 1.2, oa=True)
    ranked = rank_venues(["machine learning", "biomedicine", "toolkit"], [broad, specific])
    assert ranked[0].venue.name == "BMC Bioinformatics"
    assert ranked[0].rationale["broad_scope_penalty"] == 0.0


def test_dblp_acronym_contributes_to_conference_fit():
    conf = _v("International Conference on Machine Learning", [], 0.0)
    conf.venue_type = "conference"
    conf.dblp_acronym = "ICML"
    journal = _v("Machine Learning", [], 0.0)
    ranked = rank_venues(["ICML"], [journal, conf])
    assert ranked[0].venue.name == "International Conference on Machine Learning"
    assert ranked[0].rationale["text_fit"] == 1.0


def test_strategy_penalizes_review_journal_for_original_research():
    review = _v("Nature Reviews Drug Discovery", ["drug discovery", "pharmacology"], 12.0)
    target = _v("Computational Toxicology", ["toxicology", "machine learning"], 3.0)
    ranked = rank_venues(
        ["mitochondrial toxicity", "machine learning", "drug development"],
        [review, target],
        ms_title="Machine Learning for Interpretable Prediction of Mitochondrial Toxicity",
    )
    assert ranked[0].venue.name == "Computational Toxicology"
    assert ranked[1].rationale["article_type_fit"] < 0.5
    assert ranked[1].rationale["risk_label"] == "high"


def test_strategy_penalizes_methods_journal_without_method_novelty():
    methods = _v("Nature Methods", ["methods", "computational biology"], 18.0)
    target = _v("Computational Toxicology", ["toxicology", "machine learning"], 3.0)
    ranked = rank_venues(
        ["mitochondrial toxicity", "molecular fingerprints", "machine learning"],
        [methods, target],
        ms_title="Machine Learning for Interpretable Prediction of Mitochondrial Toxicity",
        ms_abstract="We predict mitochondrial toxicity using existing molecular fingerprints and classifiers.",
    )
    assert ranked[0].venue.name == "Computational Toxicology"
    assert ranked[1].rationale["article_type_fit"] < 0.7


def test_ambitious_strategy_keeps_broad_option_more_competitive():
    broad = _v("Science", ["science"], 30.0)
    target = _v("Computational Toxicology", ["toxicology", "machine learning"], 3.0)
    safe = rank_venues(["mitochondrial toxicity", "machine learning"], [broad, target], strategy="safe")
    ambitious = rank_venues(["mitochondrial toxicity", "machine learning"], [broad, target], strategy="ambitious")
    assert safe[0].venue.name == "Computational Toxicology"
    assert ambitious[1].score > safe[1].score


def test_low_cost_strategy_penalizes_high_apc():
    free = _v("Free Toxicology", ["toxicology"], 2.0, oa=True, apc=0)
    pricey = _v("Pricey Toxicology", ["toxicology"], 4.0, oa=True, apc=5000)
    ranked = rank_venues(["toxicology"], [pricey, free], strategy="low-cost", apc_budget_usd=1000)
    assert ranked[0].venue.name == "Free Toxicology"
    assert ranked[1].rationale["cost_fit"] < ranked[0].rationale["cost_fit"]


def test_oa_only_strategy_penalizes_non_oa():
    oa = _v("Open Toxicology", ["toxicology"], 2.0, oa=True)
    closed = _v("Closed Toxicology", ["toxicology"], 4.0, oa=False)
    ranked = rank_venues(["toxicology"], [closed, oa], strategy="oa-only", oa_preference="oa-only")
    assert ranked[0].venue.name == "Open Toxicology"
    assert "open-access-only preference" in ranked[1].rationale["risk_reasons"][0]
