from sn_lib.venues import VenueHit
from sn_lib.ranking import rank_venues, summarize_bucketed, summarize_ranked

def _v(name, concepts, impact, oa=False, apc=None, publisher=None, source="openalex"):
    return VenueHit(id=name, name=name, issn=None, publisher=publisher,
                    is_oa=oa, apc_usd=apc, impact_proxy=impact,
                    h_index=None, concepts=concepts, source=source)

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


def test_summarize_bucketed_groups_targets_and_avoids():
    target = _v("Trusted Biomedical Journal", ["biomedical machine learning"], 2.0, publisher="Known Publisher", source="openalex+scopus")
    review = _v("Systematic Reviews", ["biomedical machine learning"], 4.0, oa=True)
    ranked = rank_venues(
        ["biomedical machine learning"],
        [review, target],
        ms_title="Machine Learning-based Prediction from Clinical Omics Data",
        ms_abstract="We analyzed patient omics data and trained machine learning classifiers.",
    )
    summary = summarize_bucketed(ranked, strategy="balanced", top_n=5)
    assert summary["buckets"]["stretch"][0]["journal"] == "Trusted Biomedical Journal"
    assert summary["buckets"]["avoid"][0]["journal"] == "Systematic Reviews"
    assert summary["top"][0]["bucket"] == "stretch"


def test_summarize_bucketed_keeps_broad_megajournal_as_safe_fallback():
    broad = _v("Scientific Reports", ["biomedical machine learning"], 2.0, oa=True)
    target = _v("BMC Medical Genomics", ["medical genomics", "machine learning"], 2.0, oa=True)
    ranked = rank_venues(
        ["biomedical machine learning"],
        [broad, target],
        ms_title="Machine Learning Prediction from Biomedical Data",
        ms_abstract="We train classifiers on biomedical patient data.",
    )
    summary = summarize_bucketed(ranked, strategy="balanced", top_n=5)
    broad_rows = [row for rows in summary["buckets"].values() for row in rows if row["journal"] == "Scientific Reports"]
    assert broad_rows[0]["bucket"] == "fallback"


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
        ["toxicology", "machine learning", "drug development"],
        [review, target],
        ms_title="Machine Learning for Interpretable Prediction of Compound Toxicity",
    )
    assert ranked[0].venue.name == "Computational Toxicology"
    assert ranked[1].rationale["article_type_fit"] < 0.5
    assert ranked[1].rationale["risk_label"] == "high"


def test_strategy_penalizes_systematic_reviews_journal_for_original_research():
    review = _v("Systematic Reviews", ["meta-analysis and systematic reviews"], 4.0, oa=True)
    target = _v("Clinical Genetics", ["genetic disorders", "molecular diagnosis"], 3.0)
    ranked = rank_venues(
        ["genetic diagnosis", "biomedical machine learning", "patient cohort"],
        [review, target],
        ms_title="Machine Learning-based Prediction of a Genetic Disorder from Clinical Omics Data",
        ms_abstract="We analyzed omics data from patients and trained machine learning classifiers.",
    )
    assert ranked[0].venue.name == "Clinical Genetics"
    assert ranked[1].rationale["article_type_fit"] <= 0.1
    assert "review-only/review-focused" in ranked[1].rationale["risk_reasons"][0]


def test_balanced_ranking_caps_high_impact_review_venue_with_topical_overlap():
    review = _v("Systematic Reviews", ["machine learning", "clinical prediction", "patient cohort"], 12.0, oa=True)
    target = _v("Journal of Biomedical Informatics", ["machine learning", "clinical decision support"], 3.0, oa=True)
    ranked = rank_venues(
        ["machine learning", "clinical prediction", "patient cohort"],
        [review, target],
        strategy="balanced",
        ms_title="Machine learning prediction from clinical records",
        ms_abstract="We trained and validated machine learning models in a patient cohort.",
    )
    assert ranked[0].venue.name == "Journal of Biomedical Informatics"
    assert ranked[1].venue.name == "Systematic Reviews"
    assert ranked[1].score <= 0.25
    assert ranked[1].rationale["risk_label"] == "high"


def test_ambitious_strategy_caps_review_only_venue_even_with_high_impact():
    review = _v("Annual Review of Biomedical Science", ["biochemistry", "genetics"], 12.0)
    target = _v("Genome Biology", ["genomics", "omics", "genetic disorders"], 5.0, oa=True)
    ranked = rank_venues(
        ["genetic diagnosis", "biomedical machine learning", "patient cohort"],
        [review, target],
        strategy="ambitious",
        ms_title="Machine Learning-based Prediction of a Genetic Disorder from Clinical Omics Data",
        ms_abstract="We analyzed omics data from patients and trained machine learning classifiers.",
    )
    assert ranked[0].venue.name == "Genome Biology"
    assert ranked[1].score <= 0.25


def test_strategy_penalizes_methods_journal_without_method_novelty():
    methods = _v("Nature Methods", ["methods", "computational biology"], 18.0)
    target = _v("Computational Toxicology", ["toxicology", "machine learning"], 3.0)
    ranked = rank_venues(
        ["compound toxicity", "molecular descriptors", "machine learning"],
        [methods, target],
        ms_title="Machine Learning for Interpretable Prediction of Compound Toxicity",
        ms_abstract="We predict compound toxicity using existing molecular descriptors and classifiers.",
    )
    assert ranked[0].venue.name == "Computational Toxicology"
    assert ranked[1].rationale["article_type_fit"] < 0.7


def test_ambitious_strategy_keeps_broad_option_more_competitive():
    broad = _v("Science", ["science"], 30.0)
    target = _v("Computational Toxicology", ["toxicology", "machine learning"], 3.0)
    safe = rank_venues(["compound toxicity", "machine learning"], [broad, target], strategy="safe")
    ambitious = rank_venues(["compound toxicity", "machine learning"], [broad, target], strategy="ambitious")
    assert safe[0].venue.name == "Computational Toxicology"
    assert ambitious[1].score > safe[1].score


def test_ambitious_strategy_penalizes_weak_scope_nature_family_venue():
    weak = _v("Nature Cell Biology", ["spaceflight effects on biology"], 10.0)
    target = _v("Genome Biology", ["genomics", "omics", "genetic disorders"], 5.0, oa=True)
    ranked = rank_venues(
        ["genetic diagnosis", "biomedical machine learning", "patient cohort"],
        [weak, target],
        strategy="ambitious",
        ms_title="Machine Learning-based Prediction of a Genetic Disorder from Clinical Omics Data",
        ms_abstract="We analyzed omics data from patients and trained machine learning classifiers.",
    )
    assert ranked[0].venue.name == "Genome Biology"
    assert ranked[1].rationale["article_type_fit"] <= 0.45
    assert any("weak scope evidence" in reason for reason in ranked[1].rationale["risk_reasons"])


def test_biomedical_manuscript_penalizes_physical_science_ml_venue():
    off_scope = _v("Computer Physics Communications", ["machine learning in materials science", "physical sciences"], 3.0)
    target = _v("Computational and Structural Biotechnology Journal", ["machine learning in healthcare", "bioinformatics"], 2.0, oa=True)
    ranked = rank_venues(
        ["biomedical machine learning", "clinical omics", "patient cohort"],
        [off_scope, target],
        ms_title="Machine Learning-based Prediction from Clinical Omics Data",
        ms_abstract="We analyzed patient omics data and trained machine learning classifiers.",
    )
    assert ranked[0].venue.name == "Computational and Structural Biotechnology Journal"
    assert ranked[1].rationale["scope_fit"] <= 0.37
    assert any("scope" in reason for reason in ranked[1].rationale["risk_reasons"])
    assert any("scope" in reason for reason in ranked[1].rationale["risk_reasons"])


def test_domain_gate_prevents_generic_method_journal_from_beating_application_journal():
    method_only = _v("Machine Learning", ["artificial intelligence", "algorithms"], 8.0)
    target = _v("Journal of Biomedical Informatics", ["machine learning", "health informatics"], 3.0)
    ranked = rank_venues(
        ["biomedical machine learning", "clinical prediction", "patient cohort"],
        [method_only, target],
        ms_title="Machine learning prediction from clinical records",
        ms_abstract="We trained and validated models in a patient cohort.",
    )
    assert ranked[0].venue.name == "Journal of Biomedical Informatics"
    assert ranked[1].rationale["domain_gate"] == "method_only_match"
    assert ranked[1].score <= 0.45


def test_bucketed_summary_keeps_domain_conflicts_out_of_target_buckets():
    conflict = _v("Journal of Health Psychology", ["psychology", "social science"], 10.0)
    target = _v("ACS Catalysis", ["chemistry", "catalysis"], 3.0)
    ranked = rank_venues(
        ["organic synthesis", "catalysis"],
        [conflict, target],
        ms_title="Catalytic synthesis of organic molecules",
        ms_abstract="We report chemical synthesis and catalysis.",
    )
    summary = summarize_bucketed(ranked, strategy="balanced", top_n=5)
    conflict_rows = [row for rows in summary["buckets"].values() for row in rows if row["journal"] == "Journal of Health Psychology"]
    assert conflict_rows[0]["bucket"] == "fallback"
    assert summary["top"][0]["journal"] == "ACS Catalysis"


def test_biomedical_manuscript_penalizes_social_geography_venue():
    off_scope = _v("Social & Cultural Geography", ["geography", "social sciences"], 2.0)
    target = _v("BMC Medical Genomics", ["medical genomics", "transcriptomics"], 2.0, oa=True)
    ranked = rank_venues(
        ["mitochondrial disease", "RNA sequencing", "machine learning"],
        [off_scope, target],
        ms_title="Machine Learning-based Prediction of Mitochondrial Disease from Whole-Blood RNA Sequencing Data",
        ms_abstract="We analyzed patient RNA sequencing data and trained machine learning classifiers.",
    )
    assert ranked[0].venue.name == "BMC Medical Genomics"
    assert ranked[1].rationale["scope_fit"] <= 0.37
    assert any("outside the manuscript" in reason for reason in ranked[1].rationale["risk_reasons"])


def test_toxicology_manuscript_penalizes_off_topic_clinical_venue():
    off_scope = _v("European Heart Journal", ["cardiology", "heart failure"], 3.0)
    target = _v("Toxicological Sciences", ["toxicology", "drug safety"], 3.0)
    ranked = rank_venues(
        ["mitochondrial toxicity", "molecular fingerprints", "drug safety"],
        [off_scope, target],
        ms_title="Machine Learning for Interpretable Prediction of Mitochondrial Toxicity",
        ms_abstract="We use molecular descriptors and machine learning to predict compound toxicity.",
    )
    assert ranked[0].venue.name == "Toxicological Sciences"
    assert ranked[1].rationale["scope_fit"] <= 0.37
    assert any("scope" in reason for reason in ranked[1].rationale["risk_reasons"])


def test_biomedical_manuscript_penalizes_broad_engineering_proceedings():
    off_scope = _v("Proceedings of SPIE, the International Society for Optical Engineering", ["medical imaging", "physical sciences"], 1.0)
    target = _v("Clinical Genetics", ["genetic disorders", "molecular diagnosis"], 3.0)
    ranked = rank_venues(
        ["genetic diagnosis", "biomedical machine learning", "patient cohort"],
        [off_scope, target],
        ms_title="Machine Learning-based Prediction of a Genetic Disorder from Clinical Omics Data",
        ms_abstract="We analyzed omics data from patients and trained machine learning classifiers.",
    )
    assert ranked[0].venue.name == "Clinical Genetics"
    assert ranked[1].rationale["scope_fit"] <= 0.35


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


def test_ranking_caps_local_potential_predatory_match(tmp_config_dir):
    risky = _v(
        "High Impact Biomedical Journal",
        ["biomedical machine learning"],
        20.0,
        oa=True,
        apc=1500,
        publisher="Questionable Academic Press",
    )
    target = _v(
        "Trusted Biomedical Journal",
        ["biomedical machine learning"],
        2.0,
        publisher="Known Publisher",
        source="openalex+scopus",
    )
    (tmp_config_dir / "publisher_risk.json").write_text(
        '{"potential_predatory_publishers": ["Questionable Academic Press"]}',
        encoding="utf-8",
    )
    ranked = rank_venues(["biomedical machine learning"], [risky, target], strategy="ambitious")
    assert ranked[0].venue.name == "Trusted Biomedical Journal"
    assert ranked[1].rationale["publisher_risk_label"] == "potential_predatory_match"
    assert ranked[1].score <= 0.15
