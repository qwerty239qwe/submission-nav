from sn_lib.venues import VenueHit
from sn_lib.ranking import rank_venues

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
