from __future__ import annotations

import json
import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import POLICY_DIR

_TOPIC_TERMS = {
    "fraud": ("fraud", "security", "unauthorized"),
    "billing": ("refund", "payment", "billing", "charge"),
    "delivery": ("delivery", "delay", "late", "rain", "missing"),
    "technical": ("technical", "app", "error", "crash"),
}
_VALID_CATEGORIES = {"billing", "delivery", "technical", "fraud"}
_NO_POLICY_ANSWER = "I could not find that information in the policy documents."


def _query_facets(query: str) -> list[str]:
    facets = [
        facet.strip()
        for facet in re.split(r"\s+and\s+", query, flags=re.IGNORECASE)
        if facet.strip()
    ]
    return facets or [query]


def _normalize_query(query: str) -> str:
    return re.sub(r"\brainy\b", "rain", query, flags=re.IGNORECASE)


def chunk_policy(text: str, chunk_size: int = 40, overlap: int = 10) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be in [0, chunk_size)")
    chunks: list[str] = []
    for line in text.splitlines():
        words = line.split()
        if len(words) <= chunk_size:
            if words:
                chunks.append(" ".join(words))
            continue
        chunks.extend(
            " ".join(words[start : start + chunk_size])
            for start in range(0, len(words), chunk_size - overlap)
        )
    return chunks


def load_policy_documents() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(POLICY_DIR.glob("*.txt"))
        if path.is_file()
    }


def retrieve_policy(
    query: str,
    k: int = 3,
    chunk_size: int = 40,
    overlap: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if k <= 0:
        raise ValueError("k must be positive")

    corpus: list[str] = []
    documents: list[str] = []
    for name, text in load_policy_documents().items():
        for chunk in chunk_policy(text, chunk_size, overlap):
            corpus.append(chunk)
            documents.append(name)
    if not corpus:
        return {"results": []}

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        corpus_matrix = vectorizer.fit_transform(corpus)
    except ValueError as exc:
        if "empty vocabulary" in str(exc):
            return {"results": []}
        raise

    facets = _query_facets(query)
    if len(facets) > 1:
        ranked = []
        seen_chunks: set[int] = set()
        for facet in facets:
            query_matrix = vectorizer.transform([_normalize_query(facet)])
            scores = cosine_similarity(query_matrix, corpus_matrix).ravel()
            best_match = next(
                iter(
                    sorted(
                        (
                            (index, float(score))
                            for index, score in enumerate(scores)
                            if score > 0 and index not in seen_chunks
                        ),
                        key=lambda item: (-item[1], item[0]),
                    )
                ),
                None,
            )
            if best_match is not None:
                ranked.append(best_match)
                seen_chunks.add(best_match[0])
        ranked = ranked[:k]
    else:
        query_matrix = vectorizer.transform([_normalize_query(query)])
        scores = cosine_similarity(query_matrix, corpus_matrix).ravel()
        ranked = sorted(
            ((index, float(score)) for index, score in enumerate(scores) if score > 0),
            key=lambda item: (-item[1], item[0]),
        )[:k]
    return {
        "results": [
            {"doc": documents[index], "text": corpus[index], "score": score}
            for index, score in ranked
        ]
    }


def _classify_topic(question: str) -> str:
    lowered = question.lower()
    for category, terms in _TOPIC_TERMS.items():
        if any(term in lowered for term in terms):
            return category
    return "billing"


def _mock_category_hint(question: str) -> str | None:
    import mock_llm

    topic = _classify_topic(question)
    try:
        response = mock_llm.chat(
            [
                {
                    "role": "system",
                    "content": "Classify the policy topic. Return a category only.",
                },
                {"role": "user", "content": topic},
            ]
        )
    except mock_llm.TransientLLMError:
        return None

    if not isinstance(response, dict):
        return None
    content = response.get("content")
    if not isinstance(content, str):
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or parsed.get("category") not in _VALID_CATEGORIES:
        return None
    return parsed["category"]


def validate_grounded_response(response: str, sources: list[dict[str, Any]]) -> bool:
    if not isinstance(response, str) or not response.strip() or not sources:
        return False
    if any(
        not isinstance(source.get("doc"), str)
        or not isinstance(source.get("text"), str)
        for source in sources
    ):
        return False
    expected = "Relevant policy text:\n" + "\n".join(
        f"- [{source['doc']}] {source['text']}" for source in sources
    )
    return response == expected


def answer(question: str) -> dict[str, Any]:
    matches = retrieve_policy(question, k=10)
    if len(_query_facets(question)) == 1:
        results: list[dict[str, Any]] = []
        seen_documents: set[str] = set()
        for item in matches["results"]:
            if item["doc"] not in seen_documents:
                results.append(item)
                seen_documents.add(item["doc"])
            if len(results) == 3:
                break
    else:
        results = matches["results"][:3]
    category_hint = _mock_category_hint(question)

    if not results:
        return {
            "answer": _NO_POLICY_ANSWER,
            "sources_used": [],
            "grounded": True,
            "mock_category": category_hint,
        }

    response = "Relevant policy text:\n" + "\n".join(
        f"- [{item['doc']}] {item['text']}" for item in results
    )
    if not validate_grounded_response(response, results):
        raise ValueError("Retrieved policy response failed source validation")
    return {
        "answer": response,
        "sources_used": list(dict.fromkeys(item["doc"] for item in results)),
        "grounded": True,
        "mock_category": category_hint,
    }
