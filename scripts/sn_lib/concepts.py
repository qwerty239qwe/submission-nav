from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .cli import emit_json

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "in",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "using",
    "use", "used", "with", "within", "into", "via", "we", "our", "these", "those", "can",
    "may", "than", "such", "paper", "study", "approach", "method", "methods", "results",
    "analysis", "data", "model", "models", "based", "learning", "article", "research",
}
GENERIC_PHRASES = {
    "research article",
    "open access",
    "author summary",
    "machine learning",
    "open source",
    "most common",
}


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9-]{1,}", text.lower())


def _candidate_phrases(text: str, n_values: tuple[int, ...] = (2, 3)) -> list[str]:
    tokens = _tokenize(text)
    phrases: list[str] = []
    for n in n_values:
        for i in range(len(tokens) - n + 1):
            gram = tokens[i : i + n]
            if any(tok in STOPWORDS for tok in gram):
                continue
            if any(tok.startswith("http") for tok in gram):
                continue
            if any(re.fullmatch(r"a\d+", tok) for tok in gram):
                continue
            phrase = " ".join(gram)
            if phrase in GENERIC_PHRASES:
                continue
            phrases.append(phrase)
    return phrases


def derive_concepts(title: str, abstract: str | None, max_concepts: int = 5) -> list[str]:
    title = _normalize_space(title)
    abstract = _normalize_space(abstract or "")
    counts: Counter[str] = Counter()

    if title and title.lower() not in GENERIC_PHRASES:
        for chunk in re.split(r"\s*:\s*", title):
            chunk = _normalize_space(chunk)
            if (len(chunk.split()) >= 2 or re.search(r"[A-Za-z]+-[A-Za-z0-9]+", chunk)) and len(chunk) <= 90:
                counts[chunk.lower()] += 4
        for phrase in _candidate_phrases(title):
            counts[phrase] += 4

    for phrase in _candidate_phrases(abstract):
        counts[phrase] += 1

    concepts: list[str] = []
    for phrase, _ in counts.most_common():
        candidate = phrase.strip()
        if len(candidate) < 6 and not re.search(r"[A-Za-z]+-[A-Za-z0-9]+", candidate):
            continue
        if candidate in GENERIC_PHRASES:
            continue
        if "http" in candidate or re.search(r"\ba\d+\b", candidate):
            continue
        if any(candidate in existing or existing in candidate for existing in concepts):
            continue
        concepts.append(candidate)
        if len(concepts) >= max_concepts:
            break
    return concepts


def build_queries(concepts: list[str], max_queries: int = 4) -> list[str]:
    if not concepts:
        return []
    queries: list[str] = []
    if len(concepts) >= 2:
        queries.append(f"{concepts[0]} {concepts[1]}")
    queries.extend(concepts[:max_queries])
    deduped: list[str] = []
    for query in queries:
        q = _normalize_space(query)
        if q and q not in deduped:
            deduped.append(q)
        if len(deduped) >= max_queries:
            break
    return deduped


def _title_query(title: str) -> str:
    title = _normalize_space(title)
    if not title:
        return ""
    lowered = title.lower()
    if lowered in GENERIC_PHRASES:
        return ""
    if len(title.split()) > 22:
        return ""
    if lowered in {"article in press", "methodology", "submitted"}:
        return ""
    return title


def derive_from_summary(summary: dict, max_concepts: int = 5, max_queries: int = 4) -> dict:
    title = summary.get("title", "")
    abstract = summary.get("abstract", "")
    concepts = derive_concepts(title, abstract, max_concepts=max_concepts)
    queries = build_queries(concepts, max_queries=max_queries)
    tq = _title_query(title)
    if tq and queries and queries[0].lower().startswith(tq.lower()) and queries[0].lower() != tq.lower():
        queries = [tq, *queries[1:]]
    elif tq and all(tq.lower() != query.lower() for query in queries):
        queries = [tq, *queries][:max_queries]
    return {
        "title": title,
        "concepts": concepts,
        "queries": queries,
    }
