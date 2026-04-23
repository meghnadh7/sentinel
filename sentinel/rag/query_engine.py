from __future__ import annotations
from dataclasses import dataclass

from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import BaseQueryEngine

from sentinel.rag.index_builder import get_or_build_index


@dataclass
class RAGResponse:
    answer: str
    sources: list[dict]
    confidence: float


_index: VectorStoreIndex | None = None
_query_engine: BaseQueryEngine | None = None


def _get_query_engine() -> BaseQueryEngine:
    global _index, _query_engine
    if _query_engine is None:
        _index = get_or_build_index()
        _query_engine = _index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=5,
            verbose=False,
        )
    return _query_engine


def query_compliance(question: str) -> RAGResponse:
    engine = _get_query_engine()
    response = engine.query(question)

    sources = []
    if hasattr(response, "source_nodes"):
        for node in response.source_nodes:
            sources.append({
                "source": node.metadata.get("source", "unknown"),
                "score": float(node.score) if node.score is not None else 0.0,
                "text": node.text[:300] + "..." if len(node.text) > 300 else node.text,
            })

    avg_score = (
        sum(s["score"] for s in sources) / len(sources) if sources else 0.0
    )

    return RAGResponse(
        answer=str(response),
        sources=sources,
        confidence=avg_score,
    )


def query_with_citations(question: str, regulation: str | None = None) -> RAGResponse:
    if regulation:
        question = f"[{regulation}] {question}"
    return query_compliance(question)


def reset_index() -> None:
    global _index, _query_engine
    _index = None
    _query_engine = None
