from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from .config import Config


def slugify_journal(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "journal"


class RulesCache:
    def __init__(self, cfg: Config, journal: str):
        self.cfg = cfg
        self.journal = journal
        self.slug = slugify_journal(journal)

    @property
    def canonical_rules_path(self) -> Path:
        return self.cfg.rules_dir / f"{self.slug}.json"

    @property
    def cache_dir(self) -> Path:
        d = self.cfg.journal_rules_cache_dir / self.slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def raw_path(self) -> Path:
        return self.cache_dir / "raw.html"

    @property
    def meta_path(self) -> Path:
        return self.cache_dir / "meta.json"

    @property
    def cached_rules_path(self) -> Path:
        return self.cache_dir / "rules.json"

    def load_rules_data(self) -> dict | None:
        for path in (self.canonical_rules_path, self.cached_rules_path):
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        return None

    def load_meta(self) -> dict | None:
        if not self.meta_path.exists():
            return None
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def is_fresh(self, max_age_days: int | None) -> bool:
        if max_age_days is None:
            return True
        meta = self.load_meta()
        if not meta:
            return False
        fetched_at = meta.get("fetched_at_epoch")
        if not isinstance(fetched_at, (int, float)):
            return False
        max_age_seconds = max_age_days * 86400
        return (time.time() - float(fetched_at)) <= max_age_seconds

    def save(self, rules_payload: dict, html: str, url: str, fetch_method: str) -> None:
        encoded = html.encode("utf-8")
        meta = {
            "journal": self.journal,
            "slug": self.slug,
            "source_url": url,
            "fetched_at_epoch": time.time(),
            "content_hash": hashlib.sha256(encoded).hexdigest(),
            "fetch_method": fetch_method,
            "cache_version": 1,
        }
        self.raw_path.write_text(html, encoding="utf-8")
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        payload = dict(rules_payload)
        payload.update(
            {
                "source_url": url,
                "cache_status": "fresh-cache",
                "fetched_at": meta["fetched_at_epoch"],
                "content_hash": meta["content_hash"],
                "fetch_method": fetch_method,
                "cache_path": str(self.cache_dir),
            }
        )
        rendered = json.dumps(payload, indent=2, ensure_ascii=False)
        self.canonical_rules_path.write_text(rendered, encoding="utf-8")
        self.cached_rules_path.write_text(rendered, encoding="utf-8")
