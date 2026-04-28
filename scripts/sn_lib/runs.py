from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .config import Config


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    manifest: Path
    ms_full: Path
    ms_summary: Path
    concepts: Path


def _hash_path(path: Path) -> str:
    resolved = path.resolve()
    stat = resolved.stat()
    payload = f"{resolved}|{stat.st_mtime_ns}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def resolve_run_dir(ms_path: str | Path | None = None, run_dir: str | Path | None = None) -> Path:
    override = run_dir or os.getenv("SN_RUN_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if ms_path is None:
        raise ValueError("manuscript path required when --run-dir/SN_RUN_DIR is not set")
    manuscript = Path(ms_path)
    if not manuscript.exists():
        raise FileNotFoundError(str(manuscript))
    path = Config.load().config_dir / "runs" / _hash_path(manuscript)
    path.mkdir(parents=True, exist_ok=True)
    return path


def paths_for(ms_path: str | Path | None = None, run_dir: str | Path | None = None) -> RunPaths:
    root = resolve_run_dir(ms_path, run_dir)
    return RunPaths(
        run_dir=root,
        manifest=root / "manifest.json",
        ms_full=root / "ms.json",
        ms_summary=root / "ms_summary.json",
        concepts=root / "concepts.json",
    )


def query_filename(query: str) -> str:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:10]
    return f"venues_{digest}.json"


def slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "item"


def strategy_suffix(strategy: str, oa_preference: str = "any") -> str:
    parts = [slug(strategy)]
    if oa_preference and oa_preference != "any":
        parts.append(slug(oa_preference))
    return "_".join(parts)


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def update_manifest(run_dir: Path, ms_path: str | Path | None, verb: str, outputs: list[Path]) -> None:
    manifest_path = run_dir / "manifest.json"
    now = time.time()
    manifest = load_manifest(manifest_path)
    if not manifest:
        manifest = {"created": now, "verbs_run": []}
    manifest["updated"] = now
    if ms_path:
        manuscript = Path(ms_path)
        manifest["ms_path"] = str(manuscript)
        if manuscript.exists():
            manifest["ms_mtime_ns"] = manuscript.stat().st_mtime_ns
    verbs = manifest.setdefault("verbs_run", [])
    verbs.append({"verb": verb, "time": now, "outputs": [str(path) for path in outputs]})
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def outputs_fresh(inputs: list[Path], outputs: list[Path], force: bool = False) -> bool:
    if force:
        return False
    if not outputs or any(not path.exists() for path in outputs):
        return False
    if not inputs:
        return True
    newest_input = max(path.stat().st_mtime_ns for path in inputs if path.exists())
    return all(path.stat().st_mtime_ns >= newest_input for path in outputs)


def write_json_atomic(path: Path, payload: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


@contextmanager
def run_lock(run_dir: Path) -> Iterator[None]:
    lock_path = run_dir / ".lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+b") as handle:
        if os.name == "nt":
            import msvcrt

            deadline = time.time() + 60
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.time() > deadline:
                        raise TimeoutError(f"Timed out waiting for run lock: {lock_path}")
                    time.sleep(0.1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def list_runs() -> list[dict]:
    root = Config.load().config_dir / "runs"
    if not root.exists():
        return []
    out: list[dict] = []
    for run_dir in sorted(root.iterdir()):
        if not run_dir.is_dir():
            continue
        manifest = load_manifest(run_dir / "manifest.json")
        out.append({
            "run_dir": str(run_dir),
            "ms_path": manifest.get("ms_path"),
            "updated": manifest.get("updated"),
            "verbs": [row.get("verb") for row in manifest.get("verbs_run", [])],
        })
    return out


def clean_runs(older_than_days: int) -> list[str]:
    import shutil

    cutoff = time.time() - older_than_days * 86400
    removed: list[str] = []
    root = Config.load().config_dir / "runs"
    if not root.exists():
        return removed
    for run_dir in root.iterdir():
        if not run_dir.is_dir():
            continue
        manifest = load_manifest(run_dir / "manifest.json")
        updated = manifest.get("updated") or run_dir.stat().st_mtime
        if updated < cutoff:
            shutil.rmtree(run_dir)
            removed.append(str(run_dir))
    return removed
