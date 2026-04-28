from __future__ import annotations

from dataclasses import dataclass

from .venues import VenueHit


@dataclass(frozen=True)
class SpecialtySeed:
    journal: str
    domain: str
    confidence: float
    concepts: tuple[str, ...]


SPECIALTY_SEEDS: dict[str, tuple[SpecialtySeed, ...]] = {
    "mitochondrial_disease": (
        SpecialtySeed("Mitochondrion", "mitochondrial_disease", 0.96, ("mitochondrial disease", "mitochondria")),
        SpecialtySeed("Journal of Inherited Metabolic Disease", "mitochondrial_disease", 0.88, ("inherited metabolic disease", "rare disease")),
        SpecialtySeed("Molecular Genetics and Metabolism", "mitochondrial_disease", 0.84, ("metabolic disease", "genetics")),
        SpecialtySeed("Orphanet Journal of Rare Diseases", "mitochondrial_disease", 0.76, ("rare disease", "clinical genetics")),
    ),
    "clinical_genomics": (
        SpecialtySeed("BMC Medical Genomics", "clinical_genomics", 0.88, ("medical genomics", "clinical genomics")),
        SpecialtySeed("Human Molecular Genetics", "clinical_genomics", 0.82, ("human genetics", "genomics")),
        SpecialtySeed("Journal of Medical Genetics", "clinical_genomics", 0.82, ("medical genetics", "clinical genomics")),
        SpecialtySeed("Genetics in Medicine", "clinical_genomics", 0.76, ("medical genetics", "clinical diagnosis")),
    ),
    "bioinformatics_transcriptomics": (
        SpecialtySeed("BMC Bioinformatics", "bioinformatics_transcriptomics", 0.84, ("bioinformatics", "machine learning")),
        SpecialtySeed("Briefings in Bioinformatics", "bioinformatics_transcriptomics", 0.74, ("bioinformatics", "computational biology")),
        SpecialtySeed("Computational and Structural Biotechnology Journal", "bioinformatics_transcriptomics", 0.72, ("computational biology", "biotechnology")),
        SpecialtySeed("GigaScience", "bioinformatics_transcriptomics", 0.68, ("data science", "genomics")),
    ),
    "computational_toxicology": (
        SpecialtySeed("Computational Toxicology", "computational_toxicology", 0.94, ("computational toxicology", "toxicity prediction")),
        SpecialtySeed("Toxicology in Vitro", "computational_toxicology", 0.72, ("toxicology", "in vitro")),
        SpecialtySeed("Chemical Research in Toxicology", "computational_toxicology", 0.72, ("chemical toxicology", "molecular toxicology")),
    ),
}


QUERY_TEMPLATES: dict[str, tuple[str, ...]] = {
    "mitochondrial_disease": (
        "mitochondrial disease journal",
        "inherited metabolic disease journal",
        "rare disease genomics journal",
    ),
    "clinical_genomics": (
        "clinical genomics journal",
        "medical genomics transcriptomics journal",
        "genetic diagnosis journal",
    ),
    "bioinformatics_transcriptomics": (
        "bioinformatics transcriptomics journal",
        "RNA sequencing machine learning journal",
        "computational biology clinical prediction journal",
    ),
    "computational_toxicology": (
        "computational toxicology journal",
        "toxicity prediction machine learning journal",
    ),
}


def _norm(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _context(manuscript_summary: dict, profile: dict, concepts_payload: dict) -> str:
    concepts = concepts_payload.get("concepts") or []
    fields = [
        manuscript_summary.get("title"),
        manuscript_summary.get("abstract"),
        " ".join(manuscript_summary.get("section_headings") or []),
        " ".join(concepts),
        profile.get("data_type"),
        profile.get("claims_level"),
        profile.get("method_novelty"),
    ]
    return _norm(" ".join(field for field in fields if field))


def detect_specialties(manuscript_summary: dict, profile: dict, concepts_payload: dict) -> list[str]:
    text = _context(manuscript_summary, profile, concepts_payload)
    domains: list[str] = []
    if _has_any(text, ("mitochondrial disease", "mitochondria", "mitochondrial")):
        domains.append("mitochondrial_disease")
    if _has_any(text, ("genomics", "transcriptomics", "rna-seq", "rna sequencing", "genetic diagnosis", "whole-blood rna")):
        domains.append("clinical_genomics")
    if _has_any(text, ("machine learning", "classifier", "prediction", "bioinformatics", "transcriptomics", "rna-seq")):
        domains.append("bioinformatics_transcriptomics")
    if _has_any(text, ("toxicity", "toxicology", "molecular descriptor", "fingerprint", "compound")):
        domains.append("computational_toxicology")
    return domains


def build_specialty_plan(
    manuscript_summary: dict,
    profile: dict,
    concepts_payload: dict,
    broad: bool = False,
) -> dict:
    domains = detect_specialties(manuscript_summary, profile, concepts_payload)
    queries: list[str] = []
    seeds: list[dict] = []
    for domain in domains:
        for query in QUERY_TEMPLATES.get(domain, ()):
            if query not in queries:
                queries.append(query)
        for seed in SPECIALTY_SEEDS.get(domain, ()):
            seeds.append({
                "journal": seed.journal,
                "domain": seed.domain,
                "confidence": seed.confidence,
                "concepts": list(seed.concepts),
            })
    if not broad:
        queries = queries[:6]
        seeds = seeds[:12]
    return {"domains": domains, "queries": queries, "seed_journals": seeds}


def seed_venues_from_plan(plan: dict) -> list[VenueHit]:
    hits: list[VenueHit] = []
    for row in plan.get("seed_journals") or []:
        journal = row.get("journal")
        domain = row.get("domain")
        concepts = row.get("concepts") or []
        if not journal or not domain:
            continue
        hits.append(VenueHit(
            id=f"specialty:{domain}:{journal.casefold()}",
            name=journal,
            issn=None,
            publisher=None,
            is_oa=None,
            apc_usd=None,
            impact_proxy=None,
            h_index=None,
            concepts=concepts,
            source="specialty-seed",
            venue_type="journal",
            evidence_count=1,
            specialty_domain=domain,
            specialty_confidence=float(row.get("confidence") or 0.0),
        ))
    return hits
