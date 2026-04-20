from __future__ import annotations
import json, sqlite3, time, hashlib
from pathlib import Path

class HttpCache:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT, exp REAL)"
        )
        self._conn.commit()

    @staticmethod
    def _key(url: str, params: dict) -> str:
        raw = url + "|" + json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, url: str, params: dict):
        k = self._key(url, params)
        row = self._conn.execute("SELECT v, exp FROM cache WHERE k=?", (k,)).fetchone()
        if not row:
            return None
        v, exp = row
        if exp <= time.time():
            self._conn.execute("DELETE FROM cache WHERE k=?", (k,))
            self._conn.commit()
            return None
        return json.loads(v)

    def set(self, url: str, params: dict, value, ttl: int = 30 * 86400):
        k = self._key(url, params)
        exp = time.time() + ttl
        self._conn.execute(
            "INSERT OR REPLACE INTO cache(k,v,exp) VALUES(?,?,?)",
            (k, json.dumps(value), exp),
        )
        self._conn.commit()
