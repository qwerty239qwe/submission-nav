from sn_lib.specialty import build_specialty_plan, detect_specialties, seed_venues_from_plan


def test_specialty_plan_uses_manuscript_derived_queries_without_hardcoded_seeds():
    summary = {
        "title": "Machine Learning Prediction of Mitochondrial Toxicity from Molecular Fingerprints",
        "abstract": "We use molecular descriptors and machine learning to predict compound toxicity.",
        "section_headings": ["Methods", "Results"],
    }
    profile = {"domains": ["toxicology", "cheminformatics"], "data_type": "molecular"}
    concepts = {"concepts": ["mitochondrial toxicity", "molecular fingerprints", "drug safety"]}
    plan = build_specialty_plan(summary, profile, concepts)
    assert "toxicology" in plan["domains"]
    assert "cheminformatics" in plan["domains"]
    assert plan["seed_journals"] == []
    assert seed_venues_from_plan(plan) == []
    assert any("mitochondrial toxicity" in query for query in plan["queries"])
    assert all("mitochondrial disease" not in query for query in plan["queries"])


def test_detect_specialties_supports_non_biomedical_fields_generically():
    summary = {
        "title": "Seismic Resilience of Reinforced Concrete Bridges",
        "abstract": "This engineering study models bridge response under earthquake loading.",
        "section_headings": ["Methods", "Results"],
    }
    domains = detect_specialties(summary, {"domains": []}, {"concepts": ["civil engineering", "seismic resilience"]})
    assert "engineering" in domains
    assert "earth_science" in domains


def test_detect_specialties_supports_broad_cross_field_taxonomy():
    cases = [
        ("Bayesian causal inference for labor market policy", "economics", "data_science"),
        ("Photovoltaic battery materials science for power grids", "energy", "materials_science"),
        ("Teacher curriculum design and student learning outcomes", "education", "social_science"),
        ("Neural dynamics in cognitive neuroimaging", "neuroscience", "machine_learning"),
    ]
    for title, expected_primary, expected_secondary in cases:
        domains = detect_specialties(
            {"title": title, "abstract": title, "section_headings": []},
            {"domains": []},
            {"concepts": []},
        )
        assert expected_primary in domains
        assert expected_secondary in domains
