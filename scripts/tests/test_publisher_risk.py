import json

from sn_lib.publisher_risk import assess_publisher_risk
from sn_lib.venues import VenueHit


def _v(name, publisher=None, source="openalex", oa=False, apc=None):
    return VenueHit(
        id=name,
        name=name,
        issn=None,
        publisher=publisher,
        is_oa=oa,
        apc_usd=apc,
        impact_proxy=1.0,
        h_index=None,
        concepts=[],
        source=source,
    )


def test_trusted_signal_from_scopus_source(tmp_config_dir):
    risk = assess_publisher_risk(_v("Example Journal", publisher="Example Publisher", source="openalex+scopus"))
    assert risk.label == "trusted"
    assert "scopus" in risk.sources


def test_caution_when_open_access_apc_lacks_strong_integrity_signal(tmp_config_dir):
    risk = assess_publisher_risk(_v("Example Open Journal", publisher="Small Publisher", oa=True, apc=1800))
    assert risk.label == "caution"
    assert risk.fit < 0.7


def test_local_potential_predatory_publisher_match(tmp_config_dir):
    (tmp_config_dir / "publisher_risk.json").write_text(
        json.dumps({"potential_predatory_publishers": ["Questionable Academic Press"]}),
        encoding="utf-8",
    )
    risk = assess_publisher_risk(_v("Example Journal", publisher="Questionable Academic Press"))
    assert risk.label == "potential_predatory_match"
    assert risk.fit == 0.2


def test_local_hijacked_journal_match(tmp_config_dir):
    (tmp_config_dir / "publisher_risk.json").write_text(
        json.dumps({"hijacked_journals": ["Impersonated Journal of Medicine"]}),
        encoding="utf-8",
    )
    risk = assess_publisher_risk(_v("Impersonated Journal of Medicine", publisher="Known Publisher"))
    assert risk.label == "hijacked_or_identity_risk"
    assert risk.fit == 0.0
