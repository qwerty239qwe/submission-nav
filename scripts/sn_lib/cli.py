from __future__ import annotations

import json
import sys
from pathlib import Path


def emit_json(payload, out_path: str | None = None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        return
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
