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

def _effective_dpi(width_px: int | None, height_px: int | None, rect) -> int | None:
    if not rect or not width_px or not height_px:
        return None
    width_in = rect.width / 72.0
    height_in = rect.height / 72.0
    dpis: list[int] = []
    if width_in > 0:
        dpis.append(int(width_px / width_in))
    if height_in > 0:
        dpis.append(int(height_px / height_in))
    return min(dpis) if dpis else None

def extract_figures_from_pdf(pdf_path: str | Path) -> list[FigureInfo]:
    import fitz
    from typing import Any
    doc: Any = fitz.open(str(pdf_path))
    out: list[FigureInfo] = []
    idx = 0
    for pno in range(doc.page_count):
        page: Any = doc.load_page(pno)
        for img in page.get_images(full=True):
            xref = img[0]
            info = doc.extract_image(xref)
            idx += 1
            w = info.get("width"); h = info.get("height")
            ext = (info.get("ext") or "").upper()
            rect_list = page.get_image_rects(xref)
            dpi = _effective_dpi(w, h, rect_list[0] if rect_list else None)
            out.append(FigureInfo(idx, dpi, ext, w, h, pno + 1))
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
