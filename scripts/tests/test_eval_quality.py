from sn_lib.eval_quality import item_quality_flags, summarize_rank_quality


def test_item_quality_flags_detects_article_type_scope_and_megajournal():
    item = {
        "journal": "Scientific Reports",
        "risk_label": "high",
        "article_type_fit": 0.05,
        "venue_ambition_band": "broad_megajournal",
        "risk_reasons": ["review-only/review-focused venue", "venue appears outside the manuscript scope"],
    }

    assert item_quality_flags(item) == {
        "article_type_mismatch": True,
        "high_risk": True,
        "scope_caution": True,
        "broad_megajournal": True,
    }


def test_summarize_rank_quality_reports_rates():
    summary = summarize_rank_quality([
        {"journal": "Good Journal", "article_type_fit": 1.0, "risk_label": "low"},
        {"journal": "Systematic Reviews", "article_type_fit": 0.05, "risk_label": "high"},
    ])

    assert summary["evaluated"] == 2
    assert summary["rates"]["article_type_mismatch"] == 0.5
    assert summary["rates"]["high_risk"] == 0.5
    assert summary["has_contamination"] is True
