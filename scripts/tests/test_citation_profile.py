from sn_lib.citation_profile import (
    build_citation_profile,
    build_citation_profile_from_references,
    extract_dois,
    extract_openalex_work_ids,
    _reference_title_candidate,
    score_citation_relatedness,
)
from sn_lib.venues import VenueHit


def _venue(name, concepts, venue_id="https://openalex.org/S1"):
    return VenueHit(
        id=venue_id,
        name=name,
        issn=None,
        publisher=None,
        is_oa=None,
        apc_usd=None,
        impact_proxy=None,
        h_index=None,
        concepts=concepts,
        source="openalex",
    )


def test_extract_openalex_work_ids_from_references():
    refs = [
        "1. Prior work https://openalex.org/W12345.",
        "2. Duplicate W12345 and another W999",
    ]
    assert extract_openalex_work_ids(refs) == ["W12345", "W999"]


def test_extract_dois_from_references():
    refs = [
        "1. Example work. https://doi.org/10.1038/s41586-021-03819-2.",
        "2. Another work doi:10.1000/ABC_def",
    ]
    assert extract_dois(refs) == ["10.1038/s41586-021-03819-2", "10.1000/abc_def"]


def test_reference_title_candidate_skips_author_year_prefix():
    ref = "1. Smith J, Doe A. Interpretable models for clinical prediction using omics data. Nature Medicine. 2022."
    assert _reference_title_candidate(ref) == "Interpretable models for clinical prediction using omics data"


def test_citation_relatedness_scores_topic_and_source_overlap():
    profile = build_citation_profile([
        {
            "primary_location": {"source": {"id": "https://openalex.org/S1", "display_name": "Journal of Biomedical Informatics"}},
            "primary_topic": {
                "display_name": "Clinical prediction models",
                "field": {"display_name": "Medicine"},
                "domain": {"display_name": "Health Sciences"},
            },
            "topics": [{"display_name": "Biomedical informatics"}],
        }
    ])
    target = _venue("Journal of Biomedical Informatics", ["clinical prediction", "biomedical informatics"])
    off_scope = _venue("Machine Learning", ["artificial intelligence", "algorithms"], venue_id="https://openalex.org/S2")

    target_score = score_citation_relatedness(profile, target)
    off_scope_score = score_citation_relatedness(profile, off_scope)

    assert target_score["score"] > off_scope_score["score"]
    assert target_score["resolved_refs"] == 1


def test_build_citation_profile_resolves_openalex_doi_and_title(monkeypatch):
    calls = []

    def fake_resolve(reference):
        calls.append(reference)
        if "unresolved" in reference:
            return None
        return {
            "id": f"https://openalex.org/W{len(calls)}",
            "primary_location": {"source": {"display_name": "Journal of Biomedical Informatics"}},
            "primary_topic": {"display_name": "Biomedical informatics"},
        }

    monkeypatch.setattr("sn_lib.citation_profile._resolve_reference", fake_resolve)
    profile = build_citation_profile_from_references([
        "https://openalex.org/W1",
        "https://doi.org/10.1000/example",
        "Interpretable models for clinical prediction using omics data.",
        "unresolved reference",
    ])
    assert profile is not None
    assert profile.resolved_refs == 3
    assert profile.unresolved_refs == 1
    assert profile.source_counts["journal of biomedical informatics"] == 3
