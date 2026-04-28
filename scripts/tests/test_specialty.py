from sn_lib.ranking import rank_venues, summarize_bucketed
from sn_lib.specialty import build_specialty_plan, seed_venues_from_plan
from sn_lib.venues import VenueHit


def _synthetic_mito_summary():
    return {
        "title": "Machine Learning Prediction of Mitochondrial Disease from Whole Blood RNA Sequencing",
        "abstract": (
            "We analyze whole-blood RNA sequencing and transcriptomics data from a clinical cohort "
            "to classify mitochondrial disease using machine learning."
        ),
        "section_headings": ["RNA sequencing", "Machine learning classifiers", "Clinical cohort"],
    }


def test_specialty_plan_detects_mitochondrial_transcriptomics_without_private_examples():
    plan = build_specialty_plan(
        _synthetic_mito_summary(),
        {"data_type": "omics", "claims_level": "predictive_model"},
        {"concepts": ["mitochondrial disease", "RNA sequencing", "machine learning"]},
    )
    seed_names = {row["journal"] for row in plan["seed_journals"]}
    assert "mitochondrial_disease" in plan["domains"]
    assert "clinical_genomics" in plan["domains"]
    assert "Mitochondrion" in seed_names
    assert "BMC Medical Genomics" in seed_names


def test_specialty_seed_can_outrank_generic_broad_candidate():
    plan = build_specialty_plan(
        _synthetic_mito_summary(),
        {"data_type": "omics", "claims_level": "predictive_model"},
        {"concepts": ["mitochondrial disease", "RNA sequencing", "machine learning"]},
    )
    generic = VenueHit(
        id="generic",
        name="Generic Biomedical Reports",
        issn=None,
        publisher="Known Publisher",
        is_oa=True,
        apc_usd=None,
        impact_proxy=1.5,
        h_index=None,
        concepts=["medicine", "machine learning"],
        source="openalex",
    )
    venues = seed_venues_from_plan(plan) + [generic]
    ranked = rank_venues(
        ["mitochondrial disease", "RNA sequencing", "machine learning"],
        venues,
        ms_title=_synthetic_mito_summary()["title"],
        ms_abstract=_synthetic_mito_summary()["abstract"],
    )
    summary = summarize_bucketed(ranked, top_n=5)
    top_names = [row["journal"] for row in summary["top"][:3]]
    assert "Mitochondrion" in top_names
