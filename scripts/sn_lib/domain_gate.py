from __future__ import annotations

from dataclasses import dataclass

from .suitability import ManuscriptProfile
from .venues import VenueHit


METHOD_DOMAINS = {"computer_science", "data_science", "statistics"}

DOMAIN_TERMS = {
    "biomedical": (
        "biomedical", "medicine", "medical", "clinical", "patient", "patients", "disease",
        "diagnosis", "prognosis", "genomics", "omics", "bioinformatics", "biology",
        "molecular biology", "health sciences", "healthcare", "health informatics",
        "cancer", "cardiology", "neurology", "hematology",
    ),
    "chemistry": (
        "chemistry", "chemical", "molecule", "synthesis", "catalysis",
        "compound", "organic", "inorganic", "cheminformatics", "toxicology", "drug",
        "pharmacology",
    ),
    "materials": (
        "materials", "materials science", "polymer", "nanomaterial", "alloy", "thin film",
        "semiconductor", "crystal", "ceramic", "mxene",
    ),
    "physics": (
        "physics", "quantum", "particle", "condensed matter", "optics", "optical",
        "astronomy", "astrophysics", "instrumentation", "nuclear",
    ),
    "engineering": (
        "engineering", "mechanical", "electrical", "civil", "manufacturing", "robotics",
        "construction", "control systems", "fluid", "energy conversion",
    ),
    "environmental": (
        "environment", "environmental", "ecology", "climate", "biodiversity", "ecosystem",
        "pollution", "conservation", "sustainability", "agriculture", "food security",
    ),
    "social_science": (
        "social", "psychology", "sociology", "education", "policy", "economics",
        "migration", "inequality", "business", "management", "demography",
    ),
    "computer_science": (
        "computer science", "artificial intelligence", "machine learning", "deep learning",
        "algorithm", "software", "network", "database", "information systems",
        "computational linguistics", "computer vision",
    ),
    "data_science": (
        "statistics", "statistical", "data science", "bayesian", "regression",
        "prediction", "predictive", "modeling", "simulation",
    ),
}

ADJACENT = {
    frozenset(("biomedical", "computer_science")),
    frozenset(("biomedical", "data_science")),
    frozenset(("biomedical", "chemistry")),
    frozenset(("chemistry", "materials")),
    frozenset(("chemistry", "environmental")),
    frozenset(("materials", "physics")),
    frozenset(("materials", "engineering")),
    frozenset(("physics", "engineering")),
    frozenset(("environmental", "social_science")),
    frozenset(("environmental", "engineering")),
    frozenset(("social_science", "data_science")),
    frozenset(("computer_science", "data_science")),
}


@dataclass(frozen=True)
class DomainGate:
    label: str
    score_cap: float | None
    penalty: float
    manuscript_domains: tuple[str, ...]
    venue_domains: tuple[str, ...]
    method_domains: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "score_cap": self.score_cap,
            "penalty": self.penalty,
            "manuscript_domains": list(self.manuscript_domains),
            "venue_domains": list(self.venue_domains),
            "method_domains": list(self.method_domains),
            "reasons": list(self.reasons),
        }


def _norm(text: str | None) -> str:
    return " ".join((text or "").casefold().replace("&", "and").split())


def _domains_from_text(text: str) -> set[str]:
    domains: set[str] = set()
    for domain, terms in DOMAIN_TERMS.items():
        if any(term in text for term in terms):
            domains.add(domain)
    return domains


def _profile_domain_hints(profile: ManuscriptProfile) -> set[str]:
    hints: set[str] = set()
    for domain in profile.domains:
        if domain in {"clinical", "bioinformatics"}:
            hints.add("biomedical")
        elif domain in {"toxicology", "pharmacology"}:
            hints.update({"biomedical", "chemistry"})
        elif domain == "cheminformatics":
            hints.add("chemistry")
        elif domain == "machine_learning":
            hints.add("computer_science")
    return hints


def _is_application_aware_method_venue(venue_text: str, manuscript_domains: set[str]) -> bool:
    if "biomedical" in manuscript_domains and any(term in venue_text for term in (
        "biomedical", "medical", "medicine", "clinical", "health informatics",
        "healthcare", "health sciences", "bioinformatics", "biology",
    )):
        return True
    if "chemistry" in manuscript_domains and any(term in venue_text for term in (
        "chemical", "chemistry", "cheminformatics",
    )):
        return True
    if "environmental" in manuscript_domains and "environment" in venue_text:
        return True
    return False


def infer_manuscript_domains(
    concepts: list[str],
    title: str | None,
    abstract: str | None,
    profile: ManuscriptProfile,
) -> tuple[set[str], set[str]]:
    text = _norm(" ".join([title or "", abstract or "", " ".join(concepts)]))
    domains = _domains_from_text(text) | _profile_domain_hints(profile)
    methods = domains & METHOD_DOMAINS
    applications = domains - methods
    if not applications and domains:
        applications = set(domains)
    return applications, methods


def infer_venue_domains(venue: VenueHit) -> set[str]:
    text = _norm(" ".join([venue.name or "", venue.publisher or "", " ".join(venue.concepts)]))
    domains = _domains_from_text(text)
    if venue.dblp_acronym or venue.venue_type == "conference":
        domains.add("computer_science")
    return domains


def assess_domain_compatibility(
    concepts: list[str],
    title: str | None,
    abstract: str | None,
    profile: ManuscriptProfile,
    venue: VenueHit,
) -> DomainGate:
    manuscript_domains, method_domains = infer_manuscript_domains(concepts, title, abstract, profile)
    venue_domains = infer_venue_domains(venue)
    venue_text = _norm(" ".join([venue.name or "", " ".join(venue.concepts)]))

    if not manuscript_domains or not venue_domains:
        return DomainGate(
            "unknown", None, 0.0,
            tuple(sorted(manuscript_domains)),
            tuple(sorted(venue_domains)),
            tuple(sorted(method_domains)),
            ("insufficient domain evidence for manuscript or venue",),
        )
    if manuscript_domains & venue_domains:
        return DomainGate(
            "compatible", None, 0.0,
            tuple(sorted(manuscript_domains)),
            tuple(sorted(venue_domains)),
            tuple(sorted(method_domains)),
            ("manuscript and venue share a broad research community",),
        )
    if venue_domains <= method_domains and not _is_application_aware_method_venue(venue_text, manuscript_domains):
        return DomainGate(
            "method_only_match", 0.45, 0.04,
            tuple(sorted(manuscript_domains)),
            tuple(sorted(venue_domains)),
            tuple(sorted(method_domains)),
            ("venue matches methods but not the manuscript application community",),
        )
    if any(frozenset((left, right)) in ADJACENT for left in manuscript_domains for right in venue_domains):
        return DomainGate(
            "adjacent", 0.58, 0.02,
            tuple(sorted(manuscript_domains)),
            tuple(sorted(venue_domains)),
            tuple(sorted(method_domains)),
            ("venue is adjacent but not in the manuscript's primary community",),
        )
    return DomainGate(
        "conflict", 0.35, 0.08,
        tuple(sorted(manuscript_domains)),
        tuple(sorted(venue_domains)),
        tuple(sorted(method_domains)),
        ("venue broad domain conflicts with manuscript application community",),
    )


def apply_domain_gate(score: float, gate: DomainGate) -> float:
    adjusted = score
    if gate.score_cap is not None:
        adjusted = min(adjusted, gate.score_cap)
    adjusted -= gate.penalty
    return max(0.0, adjusted)
