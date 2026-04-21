from sn_lib.figures import check_against_rules, FigureInfo, CheckResult
from sn_lib.rules import JournalRules

def test_dpi_too_low_flags():
    figs = [FigureInfo(index=1, dpi=150, format="PNG", width_px=800, height_px=600)]
    rules = JournalRules(journal="J", source_url="", figure_dpi=300, figure_formats=["TIFF", "EPS"])
    res = check_against_rules(figs, rules, word_count=5000)
    assert any("dpi" in v.lower() for v in res.violations)
    assert any("format" in v.lower() for v in res.violations)

def test_word_limit_violation():
    rules = JournalRules(journal="J", source_url="", word_limit=4000)
    res = check_against_rules([], rules, word_count=8000)
    assert any("word" in v.lower() for v in res.violations)

def test_no_rules_no_violations():
    rules = JournalRules(journal="J", source_url="")
    res = check_against_rules([], rules, word_count=1000)
    assert res.violations == []
