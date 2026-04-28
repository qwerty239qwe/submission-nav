import respx, httpx
from sn_lib.config import Config
from sn_lib.venues import search_dblp_venues, search_openalex, search_venues, VenueHit

@respx.mock
def test_search_openalex_parses_hits(tmp_config_dir, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
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
    assert h.venue_type == "journal"

@respx.mock
def test_search_venues_uses_configured_keys(monkeypatch, tmp_config_dir):
    monkeypatch.setenv("ELSEVIER_API_KEY", "SCOPUS-KEY")
    monkeypatch.setenv("DOAJ_KEY", "DOAJ-KEY")
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
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
    scopus_route = respx.get("https://api.elsevier.com/content/serial/title").mock(
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
    respx.get("https://api.crossref.org/journals/1234-5678").mock(
        return_value=httpx.Response(200, json={
            "message": {
                "title": "Journal of Widgets",
                "publisher": "Elsevier",
                "ISSN": ["1234-5678"],
            }
        })
    )

    hits = search_venues("widget optimization", per_page=5)

    assert len(hits) == 1
    assert hits[0].impact_proxy == 2.7
    assert hits[0].apc_usd == 1500
    assert hits[0].source == "openalex-works+openalex+scopus+doaj+crossref"
    assert "Widget optimization" in hits[0].concepts
    assert hits[0].publisher == "Elsevier"
    assert scopus_route.calls[0].request.headers["X-ELS-APIKey"] == "SCOPUS-KEY"
    assert scopus_route.calls[0].request.url.params["issn"] == "1234-5678"
    assert scopus_route.calls[0].request.url.params["view"] == "STANDARD"
    assert doaj_route.calls[0].request.url.params["api_key"] == "DOAJ-KEY"


@respx.mock
def test_search_venues_uses_configured_contact_emails(tmp_config_dir, monkeypatch):
    monkeypatch.setattr("sn_lib.config._dotenv_path", lambda: tmp_config_dir / ".env")
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("OPENALEX_EMAIL", raising=False)
    monkeypatch.delenv("OPENALEX_MAILTO", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
    cfg = Config.load()
    cfg.openalex_email = "openalex@example.org"
    cfg.crossref_email = "crossref@example.org"
    cfg.save()

    works_route = respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    sources_route = respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S2", "display_name": "Journal of Crossref Widgets",
             "issn_l": "9876-5432", "is_oa": False,
             "type": "journal", "summary_stats": {}, "apc_usd": None,
             "host_organization_name": None, "x_concepts": []}
        ]})
    )
    crossref_route = respx.get("https://api.crossref.org/journals/9876-5432").mock(
        return_value=httpx.Response(200, json={"message": {"title": "Journal of Crossref Widgets"}})
    )

    hits = search_venues("widgets", per_page=5)

    assert len(hits) == 1
    assert works_route.calls[0].request.url.params["mailto"] == "openalex@example.org"
    assert sources_route.calls[0].request.url.params["mailto"] == "openalex@example.org"
    assert crossref_route.calls[0].request.url.params["mailto"] == "crossref@example.org"


@respx.mock
def test_search_venues_falls_back_to_work_sources(tmp_config_dir, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
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
    respx.get("https://api.crossref.org/journals/2468-1113").mock(
        return_value=httpx.Response(404, json={"status": "resource not found"})
    )
    respx.get("https://api.elsevier.com/content/serial/title").mock(
        return_value=httpx.Response(404, json={"service-error": {"status": {"statusCode": "NOT_FOUND"}}})
    )
    hits = search_venues("compound toxicity machine learning", per_page=5)
    assert len(hits) == 1
    assert hits[0].name == "Computational Toxicology"
    assert "Computational toxicology" in hits[0].concepts
    assert hits[0].evidence_count == 1


@respx.mock
def test_search_venues_falls_back_to_sources_when_works_query_errors(tmp_config_dir, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(400, json={"error": "bad filter"})
    )
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S1", "display_name": "Journal of Widgets",
             "issn_l": "1234-5678", "is_oa": True,
             "summary_stats": {"2yr_mean_citedness": 3.2, "h_index": 50},
             "apc_usd": 2000, "host_organization_name": "Elsevier",
             "x_concepts": [{"display_name": "Widgetry", "score": 0.9}]}
        ]})
    )
    respx.get("https://api.crossref.org/journals/1234-5678").mock(
        return_value=httpx.Response(404, json={"status": "resource not found"})
    )
    respx.get("https://api.elsevier.com/content/serial/title").mock(
        return_value=httpx.Response(404, json={"service-error": {"status": {"statusCode": "NOT_FOUND"}}})
    )
    hits = search_venues("widget optimization", per_page=5)
    assert len(hits) == 1
    assert hits[0].name == "Journal of Widgets"
    assert hits[0].source == "openalex"


@respx.mock
def test_search_venues_skips_scopus_404(tmp_config_dir, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
    cfg = Config.load()
    cfg.scopus_key = "SCOPUS-KEY"
    cfg.save()
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S1", "display_name": "Journal of Widgets",
             "issn_l": "1234-5678", "is_oa": False,
             "summary_stats": {"2yr_mean_citedness": 3.2, "h_index": 50},
             "apc_usd": None, "host_organization_name": "Elsevier",
             "x_concepts": [{"display_name": "Widgetry", "score": 0.9}]}
        ]})
    )
    respx.get("https://api.elsevier.com/content/serial/title").mock(
        return_value=httpx.Response(404, json={"service-error": {"status": {"statusCode": "NOT_FOUND"}}})
    )
    respx.get("https://api.crossref.org/journals/1234-5678").mock(
        return_value=httpx.Response(404, json={"status": "resource not found"})
    )
    hits = search_venues("widget optimization", per_page=5)
    assert len(hits) == 1
    assert hits[0].name == "Journal of Widgets"
    assert hits[0].impact_proxy == 3.2
    assert hits[0].source == "openalex"


@respx.mock
def test_search_venues_can_target_conferences(tmp_config_dir, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S99", "display_name": "NeurIPS", "issn_l": None, "is_oa": True,
             "type": "conference",
             "summary_stats": {"2yr_mean_citedness": 6.1, "h_index": 120},
             "apc_usd": None, "host_organization_name": "NeurIPS Foundation",
             "x_concepts": [{"display_name": "Machine Learning", "score": 0.9}]}
        ]})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [
            {
                "primary_location": {
                    "source": {
                        "id": "S99",
                        "display_name": "NeurIPS",
                        "issn_l": None,
                        "is_oa": True,
                        "type": "conference",
                        "host_organization_name": "NeurIPS Foundation",
                    }
                },
                "primary_topic": {"display_name": "Neural networks"},
                "topics": [{"display_name": "Deep learning"}],
            }
        ]})
    )
    respx.get("https://dblp.org/search/venue/api").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "hits": {
                    "hit": [{
                        "info": {
                            "venue": "NeurIPS",
                            "acronym": "NeurIPS",
                            "type": "Conference and Workshop Papers",
                            "url": "https://dblp.org/db/conf/nips/",
                        }
                    }]
                }
            }
        })
    )
    hits = search_venues("deep learning", per_page=5, venue_types=("conference",))
    assert len(hits) == 1
    assert hits[0].name == "NeurIPS"
    assert hits[0].venue_type == "conference"
    assert hits[0].source == "openalex-works+openalex+dblp"
    assert hits[0].dblp_acronym == "NeurIPS"
    assert hits[0].dblp_url == "https://dblp.org/db/conf/nips/"


@respx.mock
def test_search_venues_uses_crossref_as_metadata_fallback(tmp_config_dir, monkeypatch):
    monkeypatch.delenv("ELSEVIER_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_KEY", raising=False)
    monkeypatch.delenv("DOAJ_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_EMAIL", raising=False)
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S2", "display_name": "", "issn_l": "9876-5432", "is_oa": False,
             "type": "journal",
             "summary_stats": {},
             "apc_usd": None, "host_organization_name": None,
             "x_concepts": []}
        ]})
    )
    respx.get("https://api.crossref.org/journals/9876-5432").mock(
        return_value=httpx.Response(200, json={
            "message": {
                "title": "Journal of Crossref Widgets",
                "publisher": "Crossref Publisher",
                "ISSN": ["9876-5432"],
            }
        })
    )
    respx.get("https://api.elsevier.com/content/serial/title").mock(
        return_value=httpx.Response(404, json={"service-error": {"status": {"statusCode": "NOT_FOUND"}}})
    )
    hits = search_venues("widgets", per_page=5)
    assert len(hits) == 1
    assert hits[0].name == "Journal of Crossref Widgets"
    assert hits[0].publisher == "Crossref Publisher"
    assert hits[0].source == "openalex+crossref"


@respx.mock
def test_search_dblp_venues_parses_hits(tmp_config_dir):
    respx.get("https://dblp.org/search/venue/api").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "hits": {
                    "hit": [{
                        "info": {
                            "venue": "International Conference on Machine Learning",
                            "acronym": "ICML",
                            "type": "Conference and Workshop Papers",
                            "url": "https://dblp.org/db/conf/icml/",
                        }
                    }]
                }
            }
        })
    )
    hits = search_dblp_venues("International Conference on Machine Learning", max_hits=3)
    assert hits == [{
        "venue": "International Conference on Machine Learning",
        "acronym": "ICML",
        "type": "Conference and Workshop Papers",
        "url": "https://dblp.org/db/conf/icml/",
    }]
