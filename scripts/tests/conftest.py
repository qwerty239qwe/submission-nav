import pytest
from pathlib import Path

@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    d = tmp_path / "sn"
    d.mkdir()
    monkeypatch.setenv("SN_CONFIG_DIR", str(d))
    return d
