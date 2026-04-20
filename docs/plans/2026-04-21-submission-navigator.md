# Submission Navigator Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin (`submission-navigator`) containing skills that help authors choose submission venues, fetch journal rules, check formatting, and draft revisions from a manuscript PDF/DOCX.

**Architecture:** A single plugin with one shared Python helper package (`scripts/sn_lib/`) and five skills. Skills are thin markdown orchestrators that invoke helper scripts for heavy lifting (parsing, API calls, caching). Config (API keys, cache) lives in `~/.submission-navigator/` created on first use. No browser automation in MVP.

**Tech Stack:**
- Claude Code plugin format (`.claude-plugin/plugin.json`, `skills/<name>/SKILL.md`)
- Python 3.11+ helpers: `pymupdf` (PDF), `python-docx` (DOCX), `pytesseract`+`Pillow` (OCR fallback), `httpx` (HTTP), `pydantic` (schemas), `rapidfuzz` (matching), `numpy` (ranking)
- Package/project manager: [`uv`](https://docs.astral.sh/uv/) (env, lockfile, script runner — replaces pip/venv/setuptools workflow)
- Type checker: [`ty`](https://github.com/astral-sh/ty) (Astral's Python type checker — replaces mypy)
- External APIs: OpenAlex (no key), Crossref (email), DOAJ (no key), Scopus (optional key), JANE-like via OpenAlex
- Tests: `pytest`, network calls mocked with `respx`; run via `uv run pytest`

**Plugin layout:**
```
submission-navigator/
  .claude-plugin/plugin.json
  scripts/
    sn_lib/
      __init__.py
      config.py           # API key load/save, cache paths
      parse.py            # PDF/DOCX → structured manuscript
      ocr.py              # scanned-PDF fallback
      venues.py           # OpenAlex/Crossref/DOAJ clients
      ranking.py          # multi-factor scoring
      rules.py            # fetch + summarize journal rules
      figures.py          # figure/table extraction + checks
      revision.py         # diff + mock revision helper
      cache.py            # SQLite-backed cache
    pyproject.toml
    tests/
  skills/
    submission-strategist/SKILL.md
    journal-rules/SKILL.md
    format-checker/SKILL.md
    mock-revision/SKILL.md
    sn-config/SKILL.md
  README.md
```

**Shared invariants:**
- All scripts callable as `uv run uv run --project scripts python -m sn_lib.<module> <args>` with JSON stdout (from the `scripts/` dir, or via `uv run --project scripts ...`).
- Every script takes `--config-dir` (default `~/.submission-navigator`).
- All network calls cached (SQLite) keyed by URL+params; TTL 30 days.
- On missing API key, scripts degrade gracefully and emit `{"warning": "..."}` rather than crash.

---

## Task 1: Plugin scaffold & manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 1: Write plugin manifest**

`.claude-plugin/plugin.json`:
```json
{
  "name": "submission-navigator",
  "version": "0.1.0",
  "description": "AI submission strategist: analyze manuscript, rank venues, summarize rules, check formatting, draft revisions.",
  "author": {"name": "qwerty239qwe"},
  "keywords": ["academic", "publishing", "manuscript", "journal"]
}
```

- [ ] **Step 2: Write README stub**

`README.md`:
```markdown
# submission-navigator
Claude Code plugin for academic submission workflow.

## Skills
- `sn-config` — one-time setup (API keys, email).
- `submission-strategist` — rank journals for a manuscript.
- `journal-rules` — fetch + summarize author guidelines.
- `format-checker` — check figures/tables/text vs journal rules.
- `mock-revision` — draft revision response letters.

## Install
Copy plugin dir into `~/.claude/plugins/` or publish to marketplace.
```

- [ ] **Step 3: Write .gitignore**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
*.egg-info/
.submission-navigator-cache/
# uv / ty
.ty_cache/
```

Note: `uv.lock` is committed (do NOT gitignore it).

- [ ] **Step 4: Commit**

```bash
git init
git add .
git commit -m "chore: plugin scaffold"
```

---

## Task 2: Python package scaffold

**Files:**
- Create: `scripts/pyproject.toml`
- Create: `scripts/sn_lib/__init__.py`
- Create: `scripts/tests/__init__.py`
- Create: `scripts/tests/conftest.py`

- [ ] **Step 1: Write pyproject.toml**

`scripts/pyproject.toml`:
```toml
[project]
name = "sn-lib"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pymupdf>=1.24",
  "python-docx>=1.1",
  "pytesseract>=0.3.10",
  "Pillow>=10.0",
  "httpx>=0.27",
  "pydantic>=2.6",
  "rapidfuzz>=3.6",
  "numpy>=1.26",
  "platformdirs>=4.2",
]

[dependency-groups]
dev = [
  "pytest>=8",
  "respx>=0.21",
  "pytest-asyncio>=0.23",
  "ty>=0.0.1a5",
]

[tool.uv]
package = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["sn_lib"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ty.src]
include = ["sn_lib"]

[tool.ty.rules]
# tighten as the codebase matures
unresolved-import = "warn"
```

- [ ] **Step 2: Write `__init__.py`**

`scripts/sn_lib/__init__.py`:
```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Write conftest**

`scripts/tests/conftest.py`:
```python
import pytest
from pathlib import Path

@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    d = tmp_path / "sn"
    d.mkdir()
    monkeypatch.setenv("SN_CONFIG_DIR", str(d))
    return d
```

- [ ] **Step 4: Install + verify (uv)**

Prereq: `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`).

Run:
```bash
cd scripts
uv sync            # creates .venv, installs deps + dev group, writes uv.lock
uv run pytest -q   # expect: "no tests ran" exit 5 (OK — nothing yet)
uv run ty check    # expect: clean (no sources yet)
```

- [ ] **Step 5: Commit**

```bash
git add scripts/ scripts/uv.lock
git commit -m "chore: python package scaffold (uv + ty)"
```

---

## Task 3: Config module (API keys + cache paths)

**Files:**
- Create: `scripts/sn_lib/config.py`
- Create: `scripts/tests/test_config.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_config.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_config.py -v`
Expected: `ModuleNotFoundError: sn_lib.config`.

- [ ] **Step 3: Write implementation**

`scripts/sn_lib/config.py`:
```python
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
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Add CLI entry**

Append to `scripts/sn_lib/config.py`:
```python
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
```

- [ ] **Step 6: Commit**

```bash
git add scripts/sn_lib/config.py scripts/tests/test_config.py
git commit -m "feat(config): API key storage + CLI"
```

---

## Task 4: HTTP cache (SQLite)

**Files:**
- Create: `scripts/sn_lib/cache.py`
- Create: `scripts/tests/test_cache.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_cache.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_cache.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/cache.py`:
```python
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
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_cache.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/cache.py scripts/tests/test_cache.py
git commit -m "feat(cache): sqlite-backed HTTP cache"
```

---

## Task 5: Manuscript parser (PDF + DOCX)

**Files:**
- Create: `scripts/sn_lib/parse.py`
- Create: `scripts/tests/test_parse.py`
- Create: `scripts/tests/fixtures/sample.docx` (generated in test)

- [ ] **Step 1: Write failing test**

`scripts/tests/test_parse.py`:
```python
from pathlib import Path
from docx import Document
from sn_lib.parse import parse_manuscript, Manuscript

def _make_docx(path: Path):
    d = Document()
    d.add_heading("A Novel Method for Widget Optimization", 0)
    d.add_paragraph("Alice Smith, Bob Jones")
    d.add_heading("Abstract", 1)
    d.add_paragraph("We present a new approach to widget optimization using gradient methods.")
    d.add_heading("Introduction", 1)
    d.add_paragraph("Widgets are important. Prior work ignored X.")
    d.add_heading("References", 1)
    d.add_paragraph("[1] Foo 2020. [2] Bar 2021.")
    d.save(str(path))

def test_parse_docx(tmp_path):
    p = tmp_path / "s.docx"
    _make_docx(p)
    m = parse_manuscript(p)
    assert isinstance(m, Manuscript)
    assert "Widget" in m.title
    assert m.abstract and "widget" in m.abstract.lower()
    assert any("Introduction" in s.heading for s in m.sections)
    assert m.word_count > 10
    assert m.reference_count >= 2
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_parse.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/parse.py`:
```python
from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class Section:
    heading: str
    text: str

@dataclass
class Manuscript:
    title: str
    authors: list[str]
    abstract: str | None
    sections: list[Section]
    word_count: int
    reference_count: int
    source_path: str

    def to_dict(self) -> dict:
        return {**asdict(self), "sections": [asdict(s) for s in self.sections]}

HEADING_RE = re.compile(r"^(abstract|introduction|methods?|results?|discussion|conclusion|references|acknowledg(e)?ments?)\b", re.I)
REF_LINE_RE = re.compile(r"(?:^\[\d+\]|\(\d{4}\))")

def _split_headings(paragraphs: list[tuple[str, str]]) -> list[Section]:
    sections: list[Section] = []
    cur_head = "Body"
    buf: list[str] = []
    for style, text in paragraphs:
        is_h = style.startswith("Heading") or HEADING_RE.match(text.strip())
        if is_h and text.strip():
            if buf:
                sections.append(Section(cur_head, "\n".join(buf).strip()))
                buf = []
            cur_head = text.strip()
        else:
            if text.strip():
                buf.append(text)
    if buf:
        sections.append(Section(cur_head, "\n".join(buf).strip()))
    return sections

def _parse_docx(path: Path) -> Manuscript:
    from docx import Document
    doc = Document(str(path))
    paras = [(p.style.name if p.style else "", p.text) for p in doc.paragraphs]
    title = next((t for s, t in paras if s.startswith("Heading") or s == "Title"), paras[0][1] if paras else "")
    authors_line = ""
    for i, (_, t) in enumerate(paras):
        if t == title:
            if i + 1 < len(paras):
                authors_line = paras[i + 1][1]
            break
    authors = [a.strip() for a in re.split(r",| and ", authors_line) if a.strip()] if authors_line else []
    sections = _split_headings(paras)
    abstract = next((s.text for s in sections if s.heading.lower().startswith("abstract")), None)
    refs_section = next((s for s in sections if s.heading.lower().startswith("reference")), None)
    ref_count = len(re.findall(r"\[\d+\]|\(\d{4}\)", refs_section.text)) if refs_section else 0
    all_text = " ".join(s.text for s in sections)
    wc = len(all_text.split())
    return Manuscript(title.strip(), authors, abstract, sections, wc, ref_count, str(path))

def _parse_pdf(path: Path) -> Manuscript:
    import fitz
    doc = fitz.open(str(path))
    pages = [page.get_text("text") for page in doc]
    full = "\n".join(pages)
    if len(full.strip()) < 50:
        from .ocr import ocr_pdf
        full = ocr_pdf(path)
    lines = [l for l in full.splitlines() if l.strip()]
    title = lines[0] if lines else ""
    authors_line = lines[1] if len(lines) > 1 else ""
    authors = [a.strip() for a in re.split(r",| and ", authors_line) if a.strip() and len(a.strip()) < 60]
    blocks: list[tuple[str, str]] = []
    cur_head = "Body"
    cur_buf: list[str] = []
    for ln in lines:
        if HEADING_RE.match(ln.strip()):
            if cur_buf:
                blocks.append((cur_head, "\n".join(cur_buf)))
                cur_buf = []
            cur_head = ln.strip()
        else:
            cur_buf.append(ln)
    if cur_buf:
        blocks.append((cur_head, "\n".join(cur_buf)))
    sections = [Section(h, t) for h, t in blocks]
    abstract = next((s.text for s in sections if s.heading.lower().startswith("abstract")), None)
    refs_section = next((s for s in sections if s.heading.lower().startswith("reference")), None)
    ref_count = len(re.findall(r"\[\d+\]|\(\d{4}\)", refs_section.text)) if refs_section else 0
    wc = len(full.split())
    return Manuscript(title.strip(), authors, abstract, sections, wc, ref_count, str(path))

def parse_manuscript(path: str | Path) -> Manuscript:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".docx"}:
        return _parse_docx(p)
    if suffix == ".pdf":
        return _parse_pdf(p)
    raise ValueError(f"Unsupported extension: {suffix}")

def _main():
    import argparse, json, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    m = parse_manuscript(args.path)
    print(json.dumps(m.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_parse.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/parse.py scripts/tests/test_parse.py
git commit -m "feat(parse): manuscript parser (PDF + DOCX)"
```

---

## Task 6: OCR fallback

**Files:**
- Create: `scripts/sn_lib/ocr.py`
- Create: `scripts/tests/test_ocr.py`

- [ ] **Step 1: Write test (mocked tesseract)**

`scripts/tests/test_ocr.py`:
```python
from unittest.mock import patch
from pathlib import Path
from sn_lib.ocr import ocr_pdf

def test_ocr_pdf_concatenates_pages(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with patch("sn_lib.ocr._render_pages", return_value=["img1", "img2"]), \
         patch("sn_lib.ocr._tesseract", side_effect=["hello", "world"]):
        out = ocr_pdf(pdf)
    assert "hello" in out and "world" in out
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_ocr.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/ocr.py`:
```python
from __future__ import annotations
from pathlib import Path

def _render_pages(pdf_path: Path) -> list:
    import fitz
    doc = fitz.open(str(pdf_path))
    imgs = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        imgs.append(pix.tobytes("png"))
    return imgs

def _tesseract(img_bytes) -> str:
    import io, pytesseract
    from PIL import Image
    if isinstance(img_bytes, (bytes, bytearray)):
        img = Image.open(io.BytesIO(img_bytes))
    else:
        img = img_bytes
    return pytesseract.image_to_string(img)

def ocr_pdf(path: str | Path) -> str:
    pages = _render_pages(Path(path))
    return "\n\n".join(_tesseract(p) for p in pages)
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_ocr.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/ocr.py scripts/tests/test_ocr.py
git commit -m "feat(ocr): scanned-PDF fallback via tesseract"
```

---

## Task 7: Venue retrieval (OpenAlex + Crossref + DOAJ)

**Files:**
- Create: `scripts/sn_lib/venues.py`
- Create: `scripts/tests/test_venues.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_venues.py`:
```python
import respx, httpx
from sn_lib.venues import search_openalex, VenueHit

@respx.mock
def test_search_openalex_parses_hits(tmp_config_dir):
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "S1", "display_name": "Journal of Widgets",
             "issn_l": "1234-5678", "is_oa": True,
             "summary_stats": {"2yr_mean_citedness": 3.2, "h_index": 50},
             "apc_usd": 2000, "host_organization_name": "Elsevier",
             "x_concepts": [{"display_name": "Widgetry", "score": 0.9}]}
        ]})
    )
    hits = search_openalex("widget optimization", per_page=5)
    assert len(hits) == 1
    h = hits[0]
    assert isinstance(h, VenueHit)
    assert h.name == "Journal of Widgets"
    assert h.impact_proxy == 3.2
    assert h.is_oa is True
    assert h.apc_usd == 2000
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_venues.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/venues.py`:
```python
from __future__ import annotations
import httpx
from dataclasses import dataclass, asdict
from .config import Config
from .cache import HttpCache

OPENALEX_SOURCES = "https://api.openalex.org/sources"
CROSSREF_JOURNALS = "https://api.crossref.org/journals"
DOAJ_JOURNALS = "https://doaj.org/api/search/journals"

@dataclass
class VenueHit:
    id: str
    name: str
    issn: str | None
    publisher: str | None
    is_oa: bool | None
    apc_usd: float | None
    impact_proxy: float | None
    h_index: int | None
    concepts: list[str]
    source: str

    def to_dict(self) -> dict:
        return asdict(self)

def _cache() -> HttpCache:
    cfg = Config.load()
    return HttpCache(cfg.cache_dir / "http.db")

def _get(url: str, params: dict, headers: dict | None = None) -> dict:
    cache = _cache()
    hit = cache.get(url, params)
    if hit is not None:
        return hit
    r = httpx.get(url, params=params, headers=headers or {}, timeout=20)
    r.raise_for_status()
    data = r.json()
    cache.set(url, params, data)
    return data

def search_openalex(query: str, per_page: int = 25) -> list[VenueHit]:
    cfg = Config.load()
    params = {"search": query, "per-page": per_page}
    if cfg.openalex_email:
        params["mailto"] = cfg.openalex_email
    data = _get(OPENALEX_SOURCES, params)
    out: list[VenueHit] = []
    for r in data.get("results", []):
        stats = r.get("summary_stats") or {}
        out.append(VenueHit(
            id=r.get("id", ""),
            name=r.get("display_name", ""),
            issn=r.get("issn_l"),
            publisher=r.get("host_organization_name"),
            is_oa=r.get("is_oa"),
            apc_usd=r.get("apc_usd"),
            impact_proxy=stats.get("2yr_mean_citedness"),
            h_index=stats.get("h_index"),
            concepts=[c.get("display_name", "") for c in (r.get("x_concepts") or [])[:5]],
            source="openalex",
        ))
    return out

def enrich_doaj(issn: str) -> dict | None:
    if not issn:
        return None
    try:
        data = _get(f"{DOAJ_JOURNALS}/issn:{issn}", {})
    except Exception:
        return None
    results = data.get("results") or []
    return results[0] if results else None

def search_venues(query: str, per_page: int = 25) -> list[VenueHit]:
    hits = search_openalex(query, per_page=per_page)
    for h in hits:
        if h.is_oa and h.apc_usd is None and h.issn:
            d = enrich_doaj(h.issn)
            if d:
                bib = d.get("bibjson", {})
                apc = (bib.get("apc") or {}).get("max") or []
                if apc:
                    h.apc_usd = apc[0].get("price")
    return hits

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--per-page", type=int, default=25)
    args = ap.parse_args()
    hits = search_venues(args.query, per_page=args.per_page)
    print(json.dumps([h.to_dict() for h in hits], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_venues.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/venues.py scripts/tests/test_venues.py
git commit -m "feat(venues): OpenAlex + DOAJ venue retrieval"
```

---

## Task 8: Ranking module

**Files:**
- Create: `scripts/sn_lib/ranking.py`
- Create: `scripts/tests/test_ranking.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_ranking.py`:
```python
from sn_lib.venues import VenueHit
from sn_lib.ranking import rank_venues

def _v(name, concepts, impact, oa=False, apc=None):
    return VenueHit(id=name, name=name, issn=None, publisher=None,
                    is_oa=oa, apc_usd=apc, impact_proxy=impact,
                    h_index=None, concepts=concepts, source="openalex")

def test_fit_dominates_when_equal_impact():
    ms_concepts = ["widget optimization", "gradient methods"]
    v1 = _v("Good", ["widget optimization", "optimization"], 2.0)
    v2 = _v("Bad", ["astronomy", "cosmology"], 2.0)
    ranked = rank_venues(ms_concepts, [v1, v2])
    assert ranked[0].venue.name == "Good"
    assert ranked[0].score > ranked[1].score
    assert ranked[0].rationale["fit"] > ranked[1].rationale["fit"]

def test_impact_tiebreaks_when_fit_equal():
    v1 = _v("Hi", ["x"], 5.0)
    v2 = _v("Lo", ["x"], 1.0)
    ranked = rank_venues(["x"], [v1, v2])
    assert ranked[0].venue.name == "Hi"

def test_apc_penalty_when_budget_set():
    v1 = _v("Free", ["x"], 3.0, oa=True, apc=0)
    v2 = _v("Pricey", ["x"], 3.0, oa=True, apc=5000)
    ranked = rank_venues(["x"], [v1, v2], apc_budget_usd=1000)
    assert ranked[0].venue.name == "Free"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_ranking.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/ranking.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, asdict
from rapidfuzz import fuzz
from .venues import VenueHit

@dataclass
class Ranked:
    venue: VenueHit
    score: float
    rationale: dict

    def to_dict(self) -> dict:
        return {"venue": self.venue.to_dict(), "score": self.score, "rationale": self.rationale}

def _fit(ms_concepts: list[str], v_concepts: list[str]) -> float:
    if not ms_concepts or not v_concepts:
        return 0.0
    scores = []
    for mc in ms_concepts:
        best = max((fuzz.token_set_ratio(mc, vc) for vc in v_concepts), default=0)
        scores.append(best / 100.0)
    return sum(scores) / len(scores)

def _impact(impact_proxy: float | None) -> float:
    if impact_proxy is None:
        return 0.0
    import math
    return min(1.0, math.log1p(max(0.0, impact_proxy)) / math.log1p(20))

def _oa_bonus(v: VenueHit) -> float:
    return 0.1 if v.is_oa else 0.0

def _apc_penalty(apc: float | None, budget: float | None) -> float:
    if budget is None or apc is None:
        return 0.0
    if apc <= budget:
        return 0.0
    return min(0.5, (apc - budget) / max(budget, 1.0) * 0.25)

def rank_venues(
    ms_concepts: list[str],
    venues: list[VenueHit],
    apc_budget_usd: float | None = None,
    w_fit: float = 0.6,
    w_impact: float = 0.3,
    w_oa: float = 0.1,
) -> list[Ranked]:
    out: list[Ranked] = []
    for v in venues:
        fit = _fit(ms_concepts, v.concepts)
        imp = _impact(v.impact_proxy)
        oa = _oa_bonus(v)
        pen = _apc_penalty(v.apc_usd, apc_budget_usd)
        score = w_fit * fit + w_impact * imp + w_oa * oa - pen
        out.append(Ranked(v, round(score, 4), {
            "fit": round(fit, 3),
            "impact": round(imp, 3),
            "oa_bonus": round(oa, 3),
            "apc_penalty": round(pen, 3),
        }))
    out.sort(key=lambda r: r.score, reverse=True)
    return out

def _main():
    import argparse, json, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", nargs="+", required=True)
    ap.add_argument("--venues-json", required=True, help="path to JSON list from venues module")
    ap.add_argument("--apc-budget", type=float, default=None)
    args = ap.parse_args()
    raw = json.loads(open(args.venues_json, encoding="utf-8").read())
    venues = [VenueHit(**r) for r in raw]
    ranked = rank_venues(args.concepts, venues, apc_budget_usd=args.apc_budget)
    print(json.dumps([r.to_dict() for r in ranked], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_ranking.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/ranking.py scripts/tests/test_ranking.py
git commit -m "feat(ranking): multi-factor venue scoring"
```

---

## Task 9: Journal rules fetcher

**Files:**
- Create: `scripts/sn_lib/rules.py`
- Create: `scripts/tests/test_rules.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_rules.py`:
```python
import respx, httpx
from sn_lib.rules import fetch_rules, JournalRules

@respx.mock
def test_fetch_rules_from_homepage(tmp_config_dir):
    html = """<html><body>
    <h1>Author Guidelines</h1>
    <p>Manuscripts must not exceed 6000 words.</p>
    <p>Figures should be at least 300 dpi and in TIFF or EPS format.</p>
    <p>Use Vancouver reference style.</p>
    </body></html>"""
    respx.get("https://journal.example/authors").mock(
        return_value=httpx.Response(200, html)
    )
    r = fetch_rules("Example Journal", "https://journal.example/authors")
    assert isinstance(r, JournalRules)
    assert r.word_limit == 6000
    assert r.figure_dpi == 300
    assert "TIFF" in r.figure_formats or "EPS" in r.figure_formats
    assert "vancouver" in r.reference_style.lower()
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_rules.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/rules.py`:
```python
from __future__ import annotations
import re, httpx
from dataclasses import dataclass, asdict, field
from .cache import HttpCache
from .config import Config

@dataclass
class JournalRules:
    journal: str
    source_url: str
    word_limit: int | None = None
    abstract_limit: int | None = None
    figure_dpi: int | None = None
    figure_formats: list[str] = field(default_factory=list)
    table_max: int | None = None
    reference_style: str | None = None
    reference_limit: int | None = None
    raw_excerpts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

_WORD_LIMIT = re.compile(r"(?:not\s+exceed|max(?:imum)?|limit(?:ed)?\s+to|up\s+to)\s+(\d{3,5})\s+words", re.I)
_ABSTRACT_LIMIT = re.compile(r"abstract[^.]{0,60}?(\d{2,4})\s+words", re.I)
_DPI = re.compile(r"(\d{3,4})\s*dpi", re.I)
_FORMATS = re.compile(r"\b(TIFF?|EPS|PDF|PNG|JPE?G|SVG)\b", re.I)
_REF_STYLE = re.compile(r"\b(vancouver|harvard|apa|chicago|ieee|ama)\b", re.I)
_REF_LIMIT = re.compile(r"(?:max(?:imum)?|no\s+more\s+than|up\s+to|limit(?:ed)?\s+to)\s+(\d{1,3})\s+references", re.I)

def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _get(url: str) -> str:
    cfg = Config.load()
    cache = HttpCache(cfg.cache_dir / "http.db")
    hit = cache.get(url, {"kind": "html"})
    if hit is not None:
        return hit["html"]
    r = httpx.get(url, timeout=20, follow_redirects=True)
    r.raise_for_status()
    cache.set(url, {"kind": "html"}, {"html": r.text})
    return r.text

def fetch_rules(journal: str, url: str) -> JournalRules:
    html = _get(url)
    text = _strip_html(html)
    rules = JournalRules(journal=journal, source_url=url)
    m = _WORD_LIMIT.search(text)
    if m:
        rules.word_limit = int(m.group(1))
    m = _ABSTRACT_LIMIT.search(text)
    if m:
        rules.abstract_limit = int(m.group(1))
    m = _DPI.search(text)
    if m:
        rules.figure_dpi = int(m.group(1))
    rules.figure_formats = sorted({f.upper().replace("JPEG", "JPG") for f in _FORMATS.findall(text)})
    m = _REF_STYLE.search(text)
    if m:
        rules.reference_style = m.group(1).lower()
    m = _REF_LIMIT.search(text)
    if m:
        rules.reference_limit = int(m.group(1))
    for kw in ["word", "figure", "reference", "table", "abstract"]:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if kw in sent.lower() and 20 < len(sent) < 300:
                rules.raw_excerpts.append(sent.strip())
                break
    return rules

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("journal")
    ap.add_argument("url")
    args = ap.parse_args()
    r = fetch_rules(args.journal, args.url)
    print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_rules.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/rules.py scripts/tests/test_rules.py
git commit -m "feat(rules): journal guidelines fetch + extract"
```

---

## Task 10: Figure/table extractor + checker

**Files:**
- Create: `scripts/sn_lib/figures.py`
- Create: `scripts/tests/test_figures.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_figures.py`:
```python
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
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_figures.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/figures.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
from .rules import JournalRules

@dataclass
class FigureInfo:
    index: int
    dpi: int | None
    format: str | None
    width_px: int | None
    height_px: int | None
    source_page: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class CheckResult:
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ok: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

def extract_figures_from_pdf(pdf_path: str | Path) -> list[FigureInfo]:
    import fitz
    doc = fitz.open(str(pdf_path))
    out: list[FigureInfo] = []
    idx = 0
    for pno, page in enumerate(doc, start=1):
        for img in page.get_images(full=True):
            xref = img[0]
            info = doc.extract_image(xref)
            idx += 1
            w = info.get("width"); h = info.get("height")
            ext = (info.get("ext") or "").upper()
            dpi = None
            rect_list = page.get_image_rects(xref)
            if rect_list and w and h:
                rect = rect_list[0]
                rw_in = rect.width / 72.0
                if rw_in > 0:
                    dpi = int(w / rw_in)
            out.append(FigureInfo(idx, dpi, ext, w, h, pno))
    return out

def check_against_rules(figures: list[FigureInfo], rules: JournalRules, word_count: int) -> CheckResult:
    res = CheckResult()
    if rules.word_limit and word_count > rules.word_limit:
        res.violations.append(f"Word count {word_count} exceeds limit {rules.word_limit}.")
    elif rules.word_limit:
        res.ok.append(f"Word count {word_count} within limit {rules.word_limit}.")
    for f in figures:
        if rules.figure_dpi and f.dpi and f.dpi < rules.figure_dpi:
            res.violations.append(f"Figure {f.index} dpi={f.dpi} below required {rules.figure_dpi}.")
        if rules.figure_formats and f.format and f.format not in rules.figure_formats:
            res.violations.append(f"Figure {f.index} format {f.format} not in allowed {rules.figure_formats}.")
        if rules.figure_dpi and not f.dpi:
            res.warnings.append(f"Figure {f.index} dpi unknown; required {rules.figure_dpi}.")
    return res

def _main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--rules-json", required=True)
    ap.add_argument("--word-count", type=int, required=True)
    args = ap.parse_args()
    rules_data = json.loads(open(args.rules_json, encoding="utf-8").read())
    rules = JournalRules(**rules_data)
    figs = extract_figures_from_pdf(args.pdf)
    res = check_against_rules(figs, rules, args.word_count)
    print(json.dumps({"figures": [f.to_dict() for f in figs], "check": res.to_dict()}, indent=2))

if __name__ == "__main__":
    _main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_figures.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/figures.py scripts/tests/test_figures.py
git commit -m "feat(figures): extraction + rules compliance check"
```

---

## Task 11: Mock revision helper

**Files:**
- Create: `scripts/sn_lib/revision.py`
- Create: `scripts/tests/test_revision.py`

- [ ] **Step 1: Write failing test**

`scripts/tests/test_revision.py`:
```python
from sn_lib.revision import parse_reviewer_comments, build_response_skeleton

def test_parse_reviewer_comments_splits_items():
    raw = """Reviewer 1:
1. The methods section is unclear.
2. Figure 2 needs a scale bar.

Reviewer 2:
- Clarify novelty.
- Expand related work."""
    items = parse_reviewer_comments(raw)
    assert len(items) == 4
    assert items[0]["reviewer"] == "1"
    assert "methods" in items[0]["comment"].lower()
    assert items[2]["reviewer"] == "2"

def test_build_response_skeleton_structure():
    items = [{"reviewer": "1", "idx": 1, "comment": "Methods unclear."}]
    out = build_response_skeleton(items)
    assert "Reviewer 1" in out
    assert "Comment 1" in out
    assert "Response:" in out
    assert "Methods unclear." in out
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/test_revision.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`scripts/sn_lib/revision.py`:
```python
from __future__ import annotations
import re

_REVIEWER_HEAD = re.compile(r"^\s*Reviewer\s+(\d+)\s*[:\-]?\s*$", re.I | re.M)
_ITEM = re.compile(r"^\s*(?:(\d+)[.)]|[-*•])\s+(.*)$", re.M)

def parse_reviewer_comments(text: str) -> list[dict]:
    blocks: list[tuple[str, str]] = []
    positions = [(m.start(), m.group(1)) for m in _REVIEWER_HEAD.finditer(text)]
    if not positions:
        positions = [(0, "1")]
    for i, (pos, rev) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        blocks.append((rev, text[pos:end]))
    items: list[dict] = []
    for rev, blk in blocks:
        for i, m in enumerate(_ITEM.finditer(blk), start=1):
            idx = int(m.group(1)) if m.group(1) else i
            items.append({"reviewer": rev, "idx": idx, "comment": m.group(2).strip()})
    return items

def build_response_skeleton(items: list[dict]) -> str:
    lines: list[str] = ["# Response to Reviewers", ""]
    by_rev: dict[str, list[dict]] = {}
    for it in items:
        by_rev.setdefault(it["reviewer"], []).append(it)
    for rev in sorted(by_rev):
        lines.append(f"## Reviewer {rev}")
        lines.append("")
        for it in by_rev[rev]:
            lines.append(f"### Comment {it['idx']}")
            lines.append(f"> {it['comment']}")
            lines.append("")
            lines.append("**Response:** [TODO: address the comment; cite revised section/line.]")
            lines.append("")
            lines.append("**Changes in manuscript:** [TODO: quote new/changed text.]")
            lines.append("")
    return "\n".join(lines)

def _main():
    import argparse, json, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("comments_file")
    args = ap.parse_args()
    text = open(args.comments_file, encoding="utf-8").read()
    items = parse_reviewer_comments(text)
    skeleton = build_response_skeleton(items)
    print(json.dumps({"items": items, "skeleton": skeleton}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _main()
```

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/test_revision.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_lib/revision.py scripts/tests/test_revision.py
git commit -m "feat(revision): reviewer comment parse + response skeleton"
```

---

## Task 12: `sn-config` skill

**Files:**
- Create: `skills/sn-config/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: sn-config
description: Use when first using submission-navigator or when user says "set my API keys", "configure submission navigator", or mentions missing OpenAlex/Crossref/Scopus/DOAJ keys. Stores credentials in ~/.submission-navigator/config.json.
---

# submission-navigator config

## When to run
- First invocation of any submission-navigator skill.
- User asks to add/change API credentials.

## Steps
1. Show current config:
   ```bash
   uv run --project scripts python -m sn_lib.config show
   ```
2. Ask the user (one message, bulleted) whether they want to provide each of:
   - OpenAlex email (recommended, no key — just email for polite pool)
   - Crossref email
   - Scopus API key (optional)
   - DOAJ API key (optional)
3. For each value the user provides, run:
   ```bash
   uv run --project scripts python -m sn_lib.config set --key <key_name> --value "<value>"
   ```
   where `<key_name>` is one of `openalex_email`, `crossref_email`, `scopus_key`, `doaj_key`.
4. Confirm by re-running `uv run --project scripts python -m sn_lib.config show`.

## Notes
- Never echo secret keys back in plain text after saving. Show only `***` + last 4 chars.
- If user skips a key, continue — downstream skills degrade gracefully.
```

- [ ] **Step 2: Commit**

```bash
git add skills/sn-config/
git commit -m "feat(skill): sn-config"
```

---

## Task 13: `submission-strategist` skill

**Files:**
- Create: `skills/submission-strategist/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

````markdown
---
name: submission-strategist
description: Use when user wants to pick journals/venues for a manuscript, asks "where should I submit", or provides a PDF/DOCX asking for submission targets. Parses the manuscript, retrieves candidate venues, ranks them, and explains the best submission path.
---

# submission-strategist

## Inputs
- Path to manuscript (PDF or DOCX). Ask if not provided.
- Optional: APC budget USD, OA-only flag, exclude list.

## Steps

1. **Ensure config:** if `uv run --project scripts python -m sn_lib.config show` shows no `openalex_email`, invoke `sn-config` skill first.

2. **Parse manuscript:**
   ```bash
   uv run --project scripts python -m sn_lib.parse "<path>" > /tmp/sn_ms.json
   ```
   Read title, abstract, section headings, word count, reference count.

3. **Derive query concepts:** from title + abstract, extract 3–6 noun-phrase concepts. Use the abstract text as the free-text query string.

4. **Retrieve venues:**
   ```bash
   uv run --project scripts python -m sn_lib.venues "<query string>" --per-page 40 > /tmp/sn_venues.json
   ```

5. **Rank:**
   ```bash
   uv run --project scripts python -m sn_lib.ranking --concepts <c1> <c2> <c3> \
     --venues-json /tmp/sn_venues.json \
     [--apc-budget <N>] > /tmp/sn_ranked.json
   ```

6. **Present top 5–10:** table with columns: rank, journal, publisher, fit, impact_proxy, OA, APC, h-index. Then a short paragraph for the top pick explaining the rationale (fit + impact + OA fit + concerns).

7. **Recommend a submission ladder:** stretch (top by impact), target (top by combined score), safety (high fit, lower impact). Call out mismatches (e.g. OA-only manuscript but closed-access top pick).

## Output contract
- A markdown table + three-journal ladder + rationale.
- Persist ranked list path so follow-up skills (`journal-rules`, `format-checker`) can reuse it.
````

- [ ] **Step 2: Commit**

```bash
git add skills/submission-strategist/
git commit -m "feat(skill): submission-strategist"
```

---

## Task 14: `journal-rules` skill

**Files:**
- Create: `skills/journal-rules/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

````markdown
---
name: journal-rules
description: Use when user names target journals and asks for author guidelines, submission rules, word limits, figure requirements, or reference style. Fetches and summarizes journal author instructions; caches them locally.
---

# journal-rules

## Inputs
- One or more journal names. If user didn't name any, ask them to pick from the current ranked list (`/tmp/sn_ranked.json`) or type names directly.

## Steps

1. **Resolve author-guidelines URL per journal:**
   - Prefer user-supplied URL.
   - Else search OpenAlex for the journal's homepage (`host_organization`) and construct a likely author-guidelines URL, or ask the user to paste the link.
   - Do NOT guess URLs silently — confirm with the user before fetching.

2. **Fetch + extract:**
   ```bash
   uv run --project scripts python -m sn_lib.rules "<journal name>" "<guidelines url>" > <config-dir>/rules/<slug>.json
   ```

3. **Summarize per journal:** word limit, abstract limit, figure DPI, accepted figure formats, reference style, reference limit, plus 3–5 raw excerpts where extraction may be unreliable.

4. **Compare across journals:** if user gave 2+ journals, render a side-by-side table so they can see which is most restrictive.

## Output
- Structured JSON saved to cache.
- Human-readable summary in chat.
- If the page didn't yield values for a field, say "not detected" — do not hallucinate numbers.
````

- [ ] **Step 2: Commit**

```bash
git add skills/journal-rules/
git commit -m "feat(skill): journal-rules"
```

---

## Task 15: `format-checker` skill

**Files:**
- Create: `skills/format-checker/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

````markdown
---
name: format-checker
description: Use when user wants to check whether a manuscript/figures/tables meet a target journal's rules. Compares manuscript metrics and figure properties to cached journal rules and flags violations.
---

# format-checker

## Preconditions
- Rules JSON for the journal(s) must exist in `<config-dir>/rules/`. If not, invoke `journal-rules` first.
- Manuscript parsed JSON available (else run `uv run --project scripts python -m sn_lib.parse <path>`).

## Steps

1. Confirm which journal to check against. If multiple rules files exist, ask user.

2. For each target journal:
   ```bash
   uv run --project scripts python -m sn_lib.figures "<pdf path>" \
     --rules-json <config-dir>/rules/<slug>.json \
     --word-count <N> > /tmp/sn_check_<slug>.json
   ```
   Where `<N>` is from the parsed manuscript JSON.

3. **Render report:**
   - Violations (must fix): red bullets.
   - Warnings (can't verify): yellow bullets.
   - OK: green bullets.

4. **Suggest fixes** inline: e.g. "Fig 2 is 150 dpi — re-export at 300 dpi (TIFF)." Keep suggestions specific; do not prescribe how to re-export unless asked.

5. **Non-PDF source:** if original manuscript is DOCX, figure DPI may be missing. Warn the user and recommend checking original image files manually.
````

- [ ] **Step 2: Commit**

```bash
git add skills/format-checker/
git commit -m "feat(skill): format-checker"
```

---

## Task 16: `mock-revision` skill

**Files:**
- Create: `skills/mock-revision/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

````markdown
---
name: mock-revision
description: Use when user pastes reviewer comments or a decision letter and wants a point-by-point response letter draft. Parses comments, builds a response skeleton, and lets the model fill in substantive responses.
---

# mock-revision

## Inputs
- Reviewer comments (pasted text) or a path to a file containing them.

## Steps

1. Save comments to a temp file if pasted (`/tmp/sn_reviews.txt`).
2. Parse + build skeleton:
   ```bash
   uv run --project scripts python -m sn_lib.revision /tmp/sn_reviews.txt > /tmp/sn_rev.json
   ```
3. Read `skeleton` from the JSON. For each `[TODO: ...]` placeholder, draft a substantive response using the manuscript's content (re-parse manuscript if available). Cite section/line numbers.
4. Keep responses:
   - Concise (2–4 sentences).
   - Polite (thank the reviewer once per reviewer block).
   - Point to a concrete change in the manuscript OR justify not changing (with reasoning).
5. Output a complete Markdown response letter. Offer to save it to a path the user specifies.

## Boundaries
- Do NOT invent new experimental results or data.
- If a comment needs data the user hasn't provided, leave a `[NEED INPUT]` marker and list what's needed.
````

- [ ] **Step 2: Commit**

```bash
git add skills/mock-revision/
git commit -m "feat(skill): mock-revision"
```

---

## Task 17: End-to-end smoke test

**Files:**
- Create: `scripts/tests/test_e2e_smoke.py`

- [ ] **Step 1: Write smoke test**

```python
import respx, httpx
from docx import Document
from sn_lib.parse import parse_manuscript
from sn_lib.venues import search_venues
from sn_lib.ranking import rank_venues

@respx.mock
def test_end_to_end_strategy(tmp_path, tmp_config_dir):
    p = tmp_path / "m.docx"
    d = Document()
    d.add_heading("Gradient Methods for Widget Optimization", 0)
    d.add_paragraph("Alice")
    d.add_heading("Abstract", 1)
    d.add_paragraph("We optimize widgets via gradient descent.")
    d.save(str(p))
    ms = parse_manuscript(p)
    respx.get("https://api.openalex.org/sources").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": "A", "display_name": "J Widget", "issn_l": "1",
             "summary_stats": {"2yr_mean_citedness": 4.0, "h_index": 60},
             "is_oa": True, "apc_usd": 1500, "host_organization_name": "X",
             "x_concepts": [{"display_name": "Widget optimization", "score": 0.9}]},
            {"id": "B", "display_name": "J Astronomy", "issn_l": "2",
             "summary_stats": {"2yr_mean_citedness": 5.0, "h_index": 80},
             "is_oa": False, "apc_usd": None, "host_organization_name": "Y",
             "x_concepts": [{"display_name": "Astronomy", "score": 0.9}]},
        ]})
    )
    venues = search_venues(ms.abstract or ms.title, per_page=10)
    ranked = rank_venues(["widget optimization", "gradient methods"], venues)
    assert ranked[0].venue.name == "J Widget"
```

- [ ] **Step 2: Run — expect PASS**

Run: `uv run pytest tests/test_e2e_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_e2e_smoke.py
git commit -m "test: e2e smoke for strategist pipeline"
```

---

## Task 18: Publish readiness

**Files:**
- Modify: `README.md`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Expand README**

Add to `README.md`:
```markdown
## Install (manual)
1. Install [`uv`](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`).
2. Clone into `~/.claude/plugins/submission-navigator`.
3. `cd scripts && uv sync` (creates `.venv`, installs deps from `uv.lock`).
4. Restart Claude Code. Skills auto-discovered. Skills invoke helpers via `uv run --project scripts python -m sn_lib.<module>`.

## First use
Run the `sn-config` skill to store an OpenAlex email (recommended).

## Data sources
- OpenAlex (no key; email for polite pool)
- DOAJ (no key)
- Crossref (email optional)
- Scopus (key optional)

## Limitations (MVP)
- No browser form-filling.
- Figure DPI detection requires PDF source.
- Rule extraction is heuristic; always verify against the journal's own page.
```

- [ ] **Step 2: Write CHANGELOG**

```markdown
# Changelog

## 0.1.0 — 2026-04-21
- Initial release: sn-config, submission-strategist, journal-rules, format-checker, mock-revision.
```

- [ ] **Step 3: Final test + type sweep**

Run:
```bash
cd scripts
uv run pytest -q
uv run ty check
```
Expected: all tests pass; `ty` reports no errors.

- [ ] **Step 4: Commit + tag**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: publish readiness for 0.1.0"
git tag v0.1.0
```

---

## Post-MVP backlog (not in this plan)
- Browser automation for submission forms (Playwright).
- Scopus-based acceptance-rate + turnaround estimation.
- LaTeX template auto-conversion.
- Journal-specific figure re-export (ImageMagick / inkscape).
- Embedding-based fit scoring (replace rapidfuzz concept matching).
