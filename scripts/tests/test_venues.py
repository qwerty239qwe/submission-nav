import respx, httpx
from sn_lib.config import Config
from sn_lib.venues import search_openalex, search_venues, VenueHit

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

@respx.mock
def test_search_venues_uses_configured_keys(monkeypatch, tmp_config_dir):
    cfg = Config.load()
    cfg.scopus_key = "SCOPUS-KEY"
    cfg.doaj_key = "DOAJ-KEY"
    cfg.save()

    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S1", "display_name": "Journal of Widgets",
             "issn_l": "1234-5678", "is_oa": True,
             "summary_stats": {},
             "apc_usd": None, "host_organization_name": "Elsevier",
             "x_concepts": [{"display_name": "Widgetry", "score": 0.9}]}
        ]})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [
            {
                "primary_location": {
                    "source": {
                        "id": "S1",
                        "display_name": "Journal of Widgets",
                        "issn_l": "1234-5678",
                        "is_oa": True,
                        "host_organization_name": "Elsevier",
                    }
                },
                "primary_topic": {"display_name": "Widget optimization"},
                "topics": [{"display_name": "Gradient methods"}],
            }
        ]})
    )
    scopus_route = respx.get("https://api.elsevier.com/content/serial/title/issn/1234-5678").mock(
        return_value=httpx.Response(200, json={
            "serial-metadata-response": {
                "entry": [{
                    "dc:title": "Journal of Widgets",
                    "SJRList": {"SJR": [{"$": "2.7"}]}
                }]
            }
        })
    )
    doaj_route = respx.get("https://doaj.org/api/search/journals/issn:1234-5678").mock(
        return_value=httpx.Response(200, json={
            "results": [{
                "bibjson": {
                    "apc": {"max": [{"price": 1500}]}
                }
            }]
        })
    )

    hits = search_venues("widget optimization", per_page=5)

    assert len(hits) == 1
    assert hits[0].impact_proxy == 2.7
    assert hits[0].apc_usd == 1500
    assert hits[0].source == "openalex+openalex-works+scopus"
    assert "Widget optimization" in hits[0].concepts
    assert scopus_route.calls[0].request.headers["X-ELS-APIKey"] == "SCOPUS-KEY"
    assert doaj_route.calls[0].request.url.params["api_key"] == "DOAJ-KEY"


@respx.mock
def test_search_venues_falls_back_to_work_sources(tmp_config_dir):
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [
            {
                "primary_location": {
                    "source": {
                        "id": "S42",
                        "display_name": "Computational Toxicology",
                        "issn_l": "2468-1113",
                        "is_oa": False,
                        "host_organization_name": "Elsevier BV",
                    }
                },
                "primary_topic": {
                    "display_name": "Computational toxicology",
                    "field": {"display_name": "Medicine"},
                    "subfield": {"display_name": "Toxicology"},
                    "domain": {"display_name": "Health sciences"},
                },
            }
        ]})
    )
    hits = search_venues("mitochondrial toxicity machine learning", per_page=5)
    assert len(hits) == 1
    assert hits[0].name == "Computational Toxicology"
    assert "Computational toxicology" in hits[0].concepts
    assert hits[0].evidence_count == 1
