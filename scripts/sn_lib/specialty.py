from __future__ import annotations

import re

from .venues import VenueHit


GENERIC_DOMAINS = {
    "toxicology": ("toxicity", "toxicology", "toxicological", "drug safety"),
    "cheminformatics": ("cheminformatics", "molecular descriptor", "molecular fingerprint", "qsar"),
    "pharmacology": ("pharmacology", "drug discovery", "drug development"),
    "bioinformatics": ("bioinformatics", "genomics", "transcriptomics", "omics"),
    "machine_learning": ("machine learning", "deep learning", "classifier", "prediction"),
    "clinical": ("patient", "clinical", "diagnosis", "prognosis"),
    "engineering": ("engineering", "materials", "mechanical", "electrical", "civil"),
    "computer_science": ("computer science", "algorithm", "software", "network", "computing"),
    "environmental_science": ("environmental", "ecology", "climate", "biodiversity"),
    "social_science": ("social", "psychology", "sociology", "education", "policy"),
    "chemistry": ("chemistry", "chemical", "synthesis", "catalysis", "molecule"),
    "physics": ("physics", "quantum", "optical", "particle", "condensed matter"),
}


STOPWORDS = {
    "title", "abstract", "study", "using", "based", "analysis", "results", "method", "methods",
    "effect", "effects", "data", "model", "models", "new", "novel", "research", "paper",
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
        " ".join(profile.get("domains") or []),
        profile.get("data_type"),
        profile.get("claims_level"),
        profile.get("method_novelty"),
    ]
    return _norm(" ".join(field for field in fields if field))


def _clean_phrase(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]+", " ", value or "")
    words = [word for word in text.casefold().split() if word not in STOPWORDS and len(word) > 2]
    return " ".join(words[:6]).strip()


def _top_phrases(manuscript_summary: dict, concepts_payload: dict, limit: int = 8) -> list[str]:
    phrases: list[str] = []
    for raw in concepts_payload.get("concepts") or []:
        phrase = _clean_phrase(raw)
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    title = _clean_phrase(manuscript_summary.get("title") or "")
    if title and title not in phrases:
        phrases.append(title)
    return phrases[:limit]


def detect_specialties(manuscript_summary: dict, profile: dict, concepts_payload: dict) -> list[str]:
    text = _context(manuscript_summary, profile, concepts_payload)
    domains: list[str] = []
    for domain in profile.get("domains") or []:
        if domain and domain not in domains:
            domains.append(domain)
    for domain, terms in GENERIC_DOMAINS.items():
        if domain not in domains and _has_any(text, terms):
            domains.append(domain)
    return domains or ["general"]


def build_specialty_plan(
    manuscript_summary: dict,
    profile: dict,
    concepts_payload: dict,
    broad: bool = False,
) -> dict:
    domains = detect_specialties(manuscript_summary, profile, concepts_payload)
    phrases = _top_phrases(manuscript_summary, concepts_payload, limit=10 if broad else 6)
    queries: list[str] = []
    for phrase in phrases:
        for suffix in ("journal", "research journal"):
            query = f"{phrase} {suffix}"
            if query not in queries:
                queries.append(query)
    for domain in domains[:5 if broad else 3]:
        label = domain.replace("_", " ")
        query = f"{label} journal"
        if query not in queries:
            queries.append(query)
    query_limit = 12 if broad else 6
    return {
        "domains": domains,
        "queries": queries[:query_limit],
        "seed_journals": [],
        "seed_policy": "disabled; candidates are discovered dynamically from manuscript-derived venue queries",
    }


def seed_venues_from_plan(plan: dict) -> list[VenueHit]:
    return []
