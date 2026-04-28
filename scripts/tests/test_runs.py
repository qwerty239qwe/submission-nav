import json

from sn_lib.runs import clean_runs, paths_for, query_filename, update_manifest


def test_paths_for_changes_when_manuscript_changes(tmp_path, tmp_config_dir):
    ms = tmp_path / "paper.docx"
    ms.write_text("first", encoding="utf-8")
    first = paths_for(ms).run_dir
    ms.write_text("second", encoding="utf-8")
    second = paths_for(ms).run_dir
    assert first != second


def test_query_filename_is_stable():
    assert query_filename("machine learning") == query_filename("machine learning")
    assert query_filename("machine learning").startswith("venues_")


def test_update_manifest_records_outputs(tmp_path, tmp_config_dir):
    ms = tmp_path / "paper.docx"
    ms.write_text("x", encoding="utf-8")
    run = paths_for(ms)
    out = run.run_dir / "out.json"
    out.write_text("{}", encoding="utf-8")
    update_manifest(run.run_dir, ms, "parse", [out])
    data = json.loads(run.manifest.read_text(encoding="utf-8"))
    assert data["ms_path"].endswith("paper.docx")
    assert data["verbs_run"][0]["verb"] == "parse"


def test_clean_runs_removes_old_manifest(tmp_path, tmp_config_dir):
    ms = tmp_path / "paper.docx"
    ms.write_text("x", encoding="utf-8")
    run = paths_for(ms)
    run.manifest.write_text('{"updated": 1}', encoding="utf-8")
    removed = clean_runs(older_than_days=1)
    assert str(run.run_dir) in removed
    assert not run.run_dir.exists()
