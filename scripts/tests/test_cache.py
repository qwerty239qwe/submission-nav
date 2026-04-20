import time
from sn_lib.cache import HttpCache

def test_miss_then_hit(tmp_config_dir):
    c = HttpCache(tmp_config_dir / "c.db")
    assert c.get("url", {"a": 1}) is None
    c.set("url", {"a": 1}, {"body": "hi"}, ttl=60)
    assert c.get("url", {"a": 1}) == {"body": "hi"}

def test_expired(tmp_config_dir):
    c = HttpCache(tmp_config_dir / "c.db")
    c.set("u", {}, {"x": 1}, ttl=0)
    time.sleep(0.01)
    assert c.get("u", {}) is None
