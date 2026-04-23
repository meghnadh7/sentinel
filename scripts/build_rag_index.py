from __future__ import annotations
#!/usr/bin/env python3
"""Build the LlamaIndex compliance document RAG index."""

import sys
import time

sys.path.insert(0, ".")

from rich.console import Console

console = Console()


def main() -> None:
    console.print("[bold blue]Building Sentinel RAG Index[/bold blue]")
    console.print("=" * 50)

    from sentinel.rag.index_builder import build_index, DOCUMENTS_DIR, INDEX_PERSIST_DIR
    from sentinel.config import get_settings

    settings = get_settings()
    console.print(f"Documents dir: {DOCUMENTS_DIR}")
    console.print(f"Index persist dir: {INDEX_PERSIST_DIR}")
    console.print(f"Embeddings: {'local (sentence-transformers)' if settings.use_local_embeddings else 'OpenAI text-embedding-3-small'}")
    console.print()

    docs = list(DOCUMENTS_DIR.glob("*.txt")) + list(DOCUMENTS_DIR.glob("*.pdf"))
    console.print(f"Found {len(docs)} regulatory documents:")
    for doc in docs:
        console.print(f"  - {doc.name}")
    console.print()

    console.print("Building index (this may take a moment on first run)...")
    t0 = time.time()
    index = build_index(force_rebuild=True)
    elapsed = time.time() - t0

    console.print(f"[bold green]✓ Index built in {elapsed:.1f}s[/bold green]")
    console.print(f"  Persisted to: {INDEX_PERSIST_DIR}")
    console.print()

    console.print("Running test query...")
    from sentinel.rag.query_engine import query_compliance
    result = query_compliance(
        "What does SR 11-7 require for documentation of consumer-facing AI models?"
    )
    console.print(f"[dim]Query: What does SR 11-7 require for documentation?[/dim]")
    console.print(f"Answer: {result.answer[:500]}...")
    console.print(f"Sources: {len(result.sources)} nodes retrieved")
    console.print(f"Confidence: {result.confidence:.3f}")


if __name__ == "__main__":
    main()
