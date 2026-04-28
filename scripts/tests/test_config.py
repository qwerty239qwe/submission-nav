import json, os
from sn_lib.config import Config, _write_dotenv_value, _dotenv

def test_load_missing_returns_defaults(tmp_config_dir):
    cfg = Config.load()
    assert cfg.scopus_key is None
    assert cfg.config_dir == tmp_config_dir

def test_save_and_reload_roundtrip(tmp_config_dir):
    cfg = Config.load()
    cfg.scopus_key = "SECRET"
    cfg.doaj_key = "DOAJ-KEY"
    cfg.openalex_email = "openalex@example.org"
    cfg.crossref_email = "crossref@example.org"
    cfg.save()
    again = Config.load()
    assert again.scopus_key == "SECRET"
    assert again.doaj_key == "DOAJ-KEY"
    assert again.openalex_email == "openalex@example.org"
    assert again.crossref_email == "crossref@example.org"

def test_cache_dir_created(tmp_config_dir):
    cfg = Config.load()
    assert cfg.cache_dir.exists()
    assert cfg.cache_dir.is_dir()


def test_env_key_override(monkeypatch, tmp_config_dir):
    cfg = Config.load()
    cfg.scopus_key = "FILE_KEY"
    cfg.save()
    monkeypatch.setenv("ELSEVIER_API_KEY", "ENV_SCOPUS_KEY")
    assert cfg.key("scopus_key") == "ENV_SCOPUS_KEY"
    assert cfg.key("elsevier_api_key") == "ENV_SCOPUS_KEY"


def test_legacy_home_config_dir_is_used_when_new_dir_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("SN_CONFIG_DIR", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    legacy = tmp_path / ".submission-navigator"
    legacy.mkdir()
    cfg = Config.load()
    assert cfg.config_dir == legacy


def test_write_dotenv_value(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts" / "sn_lib"
    scripts_dir.mkdir(parents=True)
    fake_file = scripts_dir / "config.py"
    fake_file.write_text("", encoding="utf-8")
    monkeypatch.setattr("sn_lib.config.__file__", str(fake_file))
    _write_dotenv_value("scopus_key", "ABC123")
    _write_dotenv_value("doaj_key", "DOAJ456")
    _write_dotenv_value("openalex_email", "openalex@example.org")
    _write_dotenv_value("crossref_email", "crossref@example.org")
    values = _dotenv()
    assert values["ELSEVIER_API_KEY"] == "ABC123"
    assert values["DOAJ_KEY"] == "DOAJ456"
    assert values["OPENALEX_EMAIL"] == "openalex@example.org"
    assert values["CROSSREF_EMAIL"] == "crossref@example.org"
