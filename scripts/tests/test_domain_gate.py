from sn_lib.domain_gate import assess_domain_compatibility
from sn_lib.suitability import infer_manuscript_profile
from sn_lib.venues import VenueHit


def _venue(name, concepts):
    return VenueHit(
        id=name,
        name=name,
        issn=None,
        publisher=None,
        is_oa=None,
        apc_usd=None,
        impact_proxy=None,
        h_index=None,
        concepts=concepts,
        source="test",
    )


def test_domain_gate_marks_application_aware_method_venue_compatible():
    concepts = ["biomedical machine learning", "clinical prediction", "patient cohort"]
    profile = infer_manuscript_profile(
        concepts,
        title="Machine learning prediction from clinical records",
        abstract="We trained models in a patient cohort.",
    )
    gate = assess_domain_compatibility(
        concepts,
        "Machine learning prediction from clinical records",
        "We trained models in a patient cohort.",
        profile,
        _venue("Journal of Biomedical Informatics", ["machine learning", "health informatics"]),
    )

    assert gate.label == "compatible"


def test_domain_gate_caps_method_only_venue_for_biomedical_application():
    concepts = ["biomedical machine learning", "clinical prediction", "patient cohort"]
    profile = infer_manuscript_profile(
        concepts,
        title="Machine learning prediction from clinical records",
        abstract="We trained models in a patient cohort.",
    )
    gate = assess_domain_compatibility(
        concepts,
        "Machine learning prediction from clinical records",
        "We trained models in a patient cohort.",
        profile,
        _venue("Machine Learning", ["artificial intelligence", "algorithms"]),
    )

    assert gate.label == "method_only_match"
    assert gate.score_cap == 0.45


def test_domain_gate_marks_cross_community_conflict():
    concepts = ["organic synthesis", "catalysis"]
    profile = infer_manuscript_profile(
        concepts,
        title="Catalytic synthesis of organic molecules",
        abstract="We report chemical synthesis and catalysis.",
    )
    gate = assess_domain_compatibility(
        concepts,
        "Catalytic synthesis of organic molecules",
        "We report chemical synthesis and catalysis.",
        profile,
        _venue("Journal of Health Psychology", ["psychology", "social science"]),
    )

    assert gate.label == "conflict"
    assert gate.score_cap == 0.35


def test_domain_gate_does_not_treat_molecular_biology_as_chemistry_venue():
    concepts = ["organic synthesis", "catalysis"]
    profile = infer_manuscript_profile(
        concepts,
        title="Catalytic synthesis of organic molecules",
        abstract="We report chemical synthesis and catalysis.",
    )
    gate = assess_domain_compatibility(
        concepts,
        "Catalytic synthesis of organic molecules",
        "We report chemical synthesis and catalysis.",
        profile,
        _venue("Genome Research", ["molecular biology", "genomics"]),
    )

    assert gate.label in {"adjacent", "conflict"}
    assert "chemistry" not in gate.venue_domains


def test_domain_gate_treats_physics_venue_as_chemistry_adjacent_without_primary_signal():
    concepts = ["computational chemistry", "molecular simulation", "catalysis"]
    profile = infer_manuscript_profile(
        concepts,
        title="Computational chemistry for catalytic molecules",
        abstract="We model molecular catalysts with quantum simulations.",
    )
    gate = assess_domain_compatibility(
        concepts,
        "Computational chemistry for catalytic molecules",
        "We model molecular catalysts with quantum simulations.",
        profile,
        _venue("Physical Review Letters", ["condensed matter physics", "physical chemistry"]),
    )

    assert gate.label == "adjacent"
    assert gate.score_cap == 0.58
