from sn_lib.contribution import assess_contribution, classify_venue_ambition
from sn_lib.ranking import rank_venues, summarize_bucketed
from sn_lib.venues import VenueHit


def _summary(title: str, abstract: str, word_count: int = 5200, refs: int = 45):
    return {
        "title": title,
        "abstract": abstract,
        "section_headings": ["Abstract", "Methods", "Results", "Discussion", "Data availability"],
        "word_count": word_count,
        "reference_count": refs,
    }


def _venue(name: str, concepts: list[str], impact: float | None = None, specialty: float | None = None):
    return VenueHit(
        id=name,
        name=name,
        issn=None,
        publisher="Known Publisher",
        is_oa=False,
        apc_usd=None,
        impact_proxy=impact,
        h_index=None,
        concepts=concepts,
        source="test",
        specialty_confidence=specialty,
        specialty_domain="test_domain" if specialty else None,
    )


def test_assess_contribution_scores_strong_specialty_manuscript_without_private_examples():
    assessment = assess_contribution(
        _summary(
            "Machine Learning Prediction of Rare Disease from RNA Sequencing",
            (
                "We analyzed a clinical cohort of patients with rare disease using whole blood RNA sequencing. "
                "We developed a machine learning classifier with cross-validation, held-out test set, baseline "
                "comparisons, data availability, code repository, and a reusable software workflow."
            ),
        ),
        {"data_type": "omics", "claims_level": "predictive_model"},
    )
    assert assessment["contribution_tier"] in {"strong_specialty", "high_impact_specialty"}
    assert assessment["scores"]["clinical_relevance"] >= 0.5
    assert "elite_general" in assessment["avoid_bands"] or assessment["contribution_tier"] == "high_impact_specialty"


def test_assess_contribution_keeps_preliminary_work_conservative():
    assessment = assess_contribution(
        _summary(
            "Preliminary Biomarker Exploration in a Small Cohort",
            "This pilot study reports a small cohort and preliminary associations without external validation.",
            word_count=2200,
            refs=12,
        ),
        {"data_type": "unspecified"},
    )
    assert assessment["contribution_tier"] in {"exploratory", "solid_specialty"}
    assert assessment["scores"]["evidence_strength"] < 0.55


def test_contribution_caps_elite_general_but_allows_specialty_target():
    assessment = {
        "contribution_tier": "solid_specialty",
        "avoid_bands": ["top_clinical", "elite_general"],
        "recommended_bands": ["specialty_target", "safe_specialty", "selective_specialty"],
    }
    elite = _venue("Nature", ["rare disease", "genomics"], impact=18.0)
    specialty = _venue("Mitochondrion", ["mitochondrial disease"], impact=3.0, specialty=0.96)
    ranked = rank_venues(
        ["mitochondrial disease", "genomics"],
        [elite, specialty],
        contribution_assessment=assessment,
        ms_title="Prediction of Mitochondrial Disease",
        ms_abstract="We analyzed patient genomics data.",
    )
    assert ranked[0].venue.name == "Mitochondrion"
    assert ranked[1].rationale["venue_ambition_band"] == "elite_general"
    assert ranked[1].score <= 0.4
    bucketed = summarize_bucketed(ranked, top_n=2)
    assert bucketed["buckets"]["avoid"][0]["journal"] == "Nature"


def test_classify_venue_ambition_for_common_bands():
    assert classify_venue_ambition(_venue("Nature", [], impact=18.0)) == "elite_general"
    assert classify_venue_ambition(_venue("Scientific Reports", [], impact=1.0)) == "broad_megajournal"
    assert classify_venue_ambition(_venue("BMC Bioinformatics", [], impact=2.0)) == "specialty_target"
