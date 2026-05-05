from sn_lib.citation_profile import (
    build_citation_profile,
    extract_openalex_work_ids,
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
