from __future__ import annotations
import json, os
from dataclasses import dataclass, asdict, field
from pathlib import Path

CONFIG_FILENAME = "config.json"

def _config_dir() -> Path:
    env = os.environ.get("SN_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".submission-navigator"

@dataclass
class Config:
    openalex_email: str | None = None
    crossref_email: str | None = None
    scopus_key: str | None = None
    doaj_key: str | None = None
    config_dir: Path = field(default_factory=_config_dir)

    @property
    def cache_dir(self) -> Path:
        d = self.config_dir / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def path(self) -> Path:
        return self.config_dir / CONFIG_FILENAME

    @classmethod
    def load(cls) -> "Config":
        cdir = _config_dir()
        cdir.mkdir(parents=True, exist_ok=True)
        p = cdir / CONFIG_FILENAME
        data: dict = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            openalex_email=data.get("openalex_email"),
            crossref_email=data.get("crossref_email"),
            scopus_key=data.get("scopus_key"),
            doaj_key=data.get("doaj_key"),
            config_dir=cdir,
        )

    def save(self) -> None:
        data = {k: v for k, v in asdict(self).items() if k != "config_dir"}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _main():
    import argparse, sys, json as _json
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["show", "set"])
    ap.add_argument("--key")
    ap.add_argument("--value")
    args = ap.parse_args()
    cfg = Config.load()
    if args.action == "show":
        print(_json.dumps({k: v for k, v in asdict(cfg).items() if k != "config_dir"}, indent=2))
    else:
        if not args.key:
            print("--key required", file=sys.stderr); sys.exit(2)
        setattr(cfg, args.key, args.value)
        cfg.save()
        print(_json.dumps({"ok": True, "key": args.key}))

if __name__ == "__main__":
    _main()
