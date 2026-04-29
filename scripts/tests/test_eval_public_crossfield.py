from datetime import date

import httpx
import respx

from eval_public_crossfield import default_from_date, fetch_candidates


def test_default_from_date_uses_five_year_window():
    assert default_from_date(date(2026, 4, 30)) == "2021-04-30"


@respx.mock
def test_fetch_candidates_applies_publication_window():
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    assert fetch_candidates("widget science", from_date="2021-04-30", to_date="2026-04-30") == []

    params = route.calls[0].request.url.params
    assert params["filter"] == (
        "type:article,has_abstract:true,primary_location.source.type:journal,"
        "from_publication_date:2021-04-30,to_publication_date:2026-04-30"
    )
