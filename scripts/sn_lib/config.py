from __future__ import annotations
import json, os
from dataclasses import dataclass, asdict, field
from pathlib import Path

CONFIG_FILENAME = "config.json"
CONFIG_DIRNAME = ".submission-nav"
LEGACY_CONFIG_DIRNAME = ".submission-navigator"
KEY_ALIASES = {
    "elsevier_api_key": "scopus_key",
    "scopus_key": "scopus_key",
    "doaj_key": "doaj_key",
    "openalex_email": "openalex_email",
    "crossref_email": "crossref_email",
}

def _config_dir() -> Path:
    env = os.environ.get("SN_CONFIG_DIR")
    if env:
        return Path(env)
    home = Path.home()
    new_dir = home / CONFIG_DIRNAME
    legacy_dir = home / LEGACY_CONFIG_DIRNAME
    if new_dir.exists() or not legacy_dir.exists():
        return new_dir
    return legacy_dir


def _dotenv() -> dict[str, str]:
    env_path = _dotenv_path()
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def _dotenv_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _canonical_key(name: str) -> str | None:
    return KEY_ALIASES.get(name)


def _dotenv_key_name(name: str) -> str | None:
    canonical = _canonical_key(name)
    if canonical == "scopus_key":
        return "ELSEVIER_API_KEY"
    if canonical == "doaj_key":
        return "DOAJ_KEY"
    if canonical == "openalex_email":
        return "OPENALEX_EMAIL"
    if canonical == "crossref_email":
        return "CROSSREF_EMAIL"
    return None


def _write_dotenv_value(name: str, value: str) -> None:
    env_name = _dotenv_key_name(name)
    if env_name is None:
        raise ValueError(f"Unknown key: {name}")
    env_path = _dotenv_path()
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    prefix = f"{env_name}="
    updated = False
    for idx, line in enumerate(lines):
        if line.strip().startswith(prefix):
            lines[idx] = f"{env_name}={value}"
            updated = True
            break
    if not updated:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{env_name}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

@dataclass
class Config:
    scopus_key: str | None = None
    doaj_key: str | None = None
    openalex_email: str | None = None
    crossref_email: str | None = None
    config_dir: Path = field(default_factory=_config_dir)

    @property
    def cache_dir(self) -> Path:
        d = self.config_dir / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def rules_dir(self) -> Path:
        d = self.config_dir / "rules"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def journal_rules_cache_dir(self) -> Path:
        d = self.cache_dir / "journal_rules"
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
            scopus_key=data.get("scopus_key"),
            doaj_key=data.get("doaj_key"),
            openalex_email=data.get("openalex_email"),
            crossref_email=data.get("crossref_email"),
            config_dir=cdir,
        )

    def key(self, name: str) -> str | None:
        canonical = _canonical_key(name)
        if canonical is None:
            return None
        env = _env_key_overrides().get(canonical)
        return env if env is not None else getattr(self, canonical)

    def save(self) -> None:
        data = {k: v for k, v in asdict(self).items() if k != "config_dir"}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _masked(val: str | None) -> str | None:
    if val is None:
        return None
    if len(val) <= 4:
        return "*" * len(val)
    return "*" * (len(val) - 4) + val[-4:]


def _env_key_overrides() -> dict[str, str | None]:
    dotenv_values = _dotenv()
    return {
        "scopus_key": os.getenv("ELSEVIER_API_KEY", dotenv_values.get("ELSEVIER_API_KEY"))
        or os.getenv("SCOPUS_KEY", dotenv_values.get("SCOPUS_KEY")),
        "doaj_key": os.getenv("DOAJ_KEY", dotenv_values.get("DOAJ_KEY")),
        "openalex_email": os.getenv("OPENALEX_EMAIL", dotenv_values.get("OPENALEX_EMAIL"))
        or os.getenv("OPENALEX_MAILTO", dotenv_values.get("OPENALEX_MAILTO")),
        "crossref_email": os.getenv("CROSSREF_EMAIL", dotenv_values.get("CROSSREF_EMAIL")),
    }
