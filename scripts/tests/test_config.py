import json, os
from sn_lib.config import Config

def test_load_missing_returns_defaults(tmp_config_dir):
    cfg = Config.load()
    assert cfg.openalex_email is None
    assert cfg.scopus_key is None
    assert cfg.config_dir == tmp_config_dir

def test_save_and_reload_roundtrip(tmp_config_dir):
    cfg = Config.load()
    cfg.openalex_email = "a@b.com"
    cfg.scopus_key = "SECRET"
    cfg.save()
    again = Config.load()
    assert again.openalex_email == "a@b.com"
    assert again.scopus_key == "SECRET"

def test_cache_dir_created(tmp_config_dir):
    cfg = Config.load()
    assert cfg.cache_dir.exists()
    assert cfg.cache_dir.is_dir()
