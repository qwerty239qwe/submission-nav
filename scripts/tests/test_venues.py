import respx, httpx
from sn_lib.venues import search_openalex, VenueHit

@respx.mock
def test_search_openalex_parses_hits(tmp_config_dir):
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S1", "display_name": "Journal of Widgets",
             "issn_l": "1234-5678", "is_oa": True,
             "summary_stats": {"2yr_mean_citedness": 3.2, "h_index": 50},
             "apc_usd": 2000, "host_organization_name": "Elsevier",
             "x_concepts": [{"display_name": "Widgetry", "score": 0.9}]}
        ]})
    )
    hits = search_openalex("widget optimization", per_page=5)
    assert len(hits) == 1
    h = hits[0]
    assert isinstance(h, VenueHit)
    assert h.name == "Journal of Widgets"
    assert h.impact_proxy == 3.2
    assert h.is_oa is True
    assert h.apc_usd == 2000
