from __future__ import annotations

import re

from .suitability import infer_manuscript_profile


def _norm(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _method_novelty(text: str) -> str:
    if _has_any(text, ("novel algorithm", "new algorithm", "new method", "novel method", "we propose", "we introduce")):
        return "new_method"
    if _has_any(text, ("benchmark", "comparison", "compare", "state-of-the-art")):
        return "benchmarking"
    if _has_any(text, ("using existing", "existing classifier", "existing model", "random forest", "support vector", "neural network")):
        return "application"
    return "unclear"


def _clinical_validation(text: str) -> str:
    if _has_any(text, ("prospective", "randomized", "clinical trial", "external validation", "independent validation cohort")):
        return "strong"
    if _has_any(text, ("patient", "patients", "cohort", "diagnosis", "clinical")):
        return "cohort"
    return "none_detected"


def _data_type(text: str) -> str:
    patterns = (
        ("omics", ("multi-omics", "omics", "genomics", "transcriptomics", "rna-seq", "sequencing")),
        ("clinical_records", ("electronic health record", "ehr", "clinical records")),
        ("molecular", ("molecular descriptor", "fingerprint", "compound", "chemical")),
        ("imaging", ("image", "imaging", "radiology", "microscopy")),
    )
    for label, terms in patterns:
        if _has_any(text, terms):
            return label
    return "unspecified"


def _claims_level(text: str) -> str:
    if _has_any(text, ("clinical utility", "decision support", "prospective", "deployed", "implementation")):
        return "clinical_utility"
    if _has_any(text, ("diagnosis", "prognosis", "classification", "classifier", "prediction")):
        return "predictive_model"
    if _has_any(text, ("mechanism", "pathway", "biological insight")):
        return "biological_insight"
    return "descriptive"


def build_profile(
    manuscript_summary: dict,
    concepts_payload: dict | None = None,
    oa_preference: str = "any",
) -> dict:
    concepts = (concepts_payload or {}).get("concepts") or []
    title = clean_title(manuscript_summary.get("title"))
    abstract = manuscript_summary.get("abstract") or ""
    headings = manuscript_summary.get("section_headings") or []
    text = _norm(" ".join([title, abstract, " ".join(concepts), " ".join(headings)]))
    base = infer_manuscript_profile(concepts, title=title, abstract=abstract, oa_preference=oa_preference)
    software_resource = _has_any(text, ("software", "application", "web server", "desktop application", "package", "toolkit"))
    dataset_resource = _has_any(text, ("dataset", "database", "data resource", "benchmark dataset"))
    return {
        **base.to_dict(),
        "data_type": _data_type(text),
        "method_novelty": _method_novelty(text),
        "clinical_validation": _clinical_validation(text),
        "software_resource": software_resource,
        "dataset_resource": dataset_resource,
        "claims_level": _claims_level(text),
        "evidence": {
            "title": title,
            "word_count": manuscript_summary.get("word_count"),
            "reference_count": manuscript_summary.get("reference_count"),
            "concepts": concepts[:8],
        },
    }


def clean_title(title: str | None) -> str:
    return re.sub(r"^\s*title\s*:\s*", "", title or "", flags=re.IGNORECASE).strip()
