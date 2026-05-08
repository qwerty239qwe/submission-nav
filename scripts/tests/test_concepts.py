from sn_lib.concepts import derive_concepts, build_queries, derive_from_summary


def test_derive_concepts_prefers_title_phrases():
    title = "Galaxy-ML: An accessible, reproducible, and scalable machine learning toolkit for biomedicine"
    abstract = "The toolkit enables reproducible supervised machine learning analyses for biomedical scientists."
    concepts = derive_concepts(title, abstract, max_concepts=5)
    assert any("galaxy-ml" in concept for concept in concepts)
    assert any("toolkit for biomedicine" in concept or "machine learning toolkit" in concept for concept in concepts)


def test_build_queries_deduplicates_and_limits():
    queries = build_queries(["whole genome data", "campylobacteriosis source attribution", "whole genome data"], max_queries=3)
    assert queries[0] == "whole genome data campylobacteriosis source attribution"
    assert len(queries) <= 3


def test_derive_from_summary_returns_queries():
    payload = derive_from_summary({
        "title": "Machine learning to predict the source of campylobacteriosis using whole genome data",
        "abstract": "We use machine learning and whole genome data for source attribution.",
    })
    assert payload["concepts"]
    assert payload["queries"]
    assert payload["queries"][0] == "Machine learning to predict the source of campylobacteriosis using whole genome data"


def test_derive_from_summary_tries_specific_title_query_before_abstract_terms():
    payload = derive_from_summary({
        "title": "Bayesian inference of mixed Gaussian phylogenetic models",
        "abstract": "Ancestral value estimation uses phylogenetic tree posterior distribution methods.",
    })
    assert payload["queries"][0] == "Bayesian inference of mixed Gaussian phylogenetic models"


def test_derive_concepts_preserves_electrocatalysis_phrases():
    concepts = derive_concepts(
        "Revealing the reaction pathways and interfacial regulation mechanisms of urea electro-oxidation on nickel-based catalysts",
        "This review summarizes electrocatalytic urea oxidation, nickel catalysts, hydrogen production, and electrochemical energy conversion.",
    )
    assert "urea electro-oxidation" in concepts
    assert "nickel-based catalysts" in concepts
    assert any("electrocatal" in concept for concept in concepts)


def test_derive_concepts_preserves_cybersecurity_economics_phrases():
    concepts = derive_concepts(
        "The Adversarial Discount AI, Signal Correlation, and the Cybersecurity Arms Race",
        "Keywords: cybersecurity economics, AI arms race, adversarial discount, signal correlation, platform security, game theory.",
    )
    assert "cybersecurity economics" in concepts
    assert "AI arms race" in concepts
    assert "game theory" in concepts
