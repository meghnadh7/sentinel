from __future__ import annotations
import os
from pathlib import Path

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter

from sentinel.config import get_settings

app_settings = get_settings()

DOCUMENTS_DIR = Path(__file__).parent / "documents"
INDEX_PERSIST_DIR = Path(app_settings.rag_index_persist_dir)


def _configure_embeddings() -> None:
    if app_settings.use_local_embeddings:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    else:
        from llama_index.embeddings.openai import OpenAIEmbedding
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    Settings.node_parser = SentenceSplitter(
        chunk_size=app_settings.rag_chunk_size,
        chunk_overlap=app_settings.rag_chunk_overlap,
    )


def build_index(force_rebuild: bool = False) -> VectorStoreIndex:
    _configure_embeddings()
    INDEX_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    if not force_rebuild and (INDEX_PERSIST_DIR / "docstore.json").exists():
        storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_PERSIST_DIR))
        return load_index_from_storage(storage_context)

    documents = SimpleDirectoryReader(
        input_dir=str(DOCUMENTS_DIR),
        required_exts=[".txt", ".pdf"],
        recursive=True,
    ).load_data()

    for doc in documents:
        doc.metadata["source"] = Path(doc.metadata.get("file_path", "unknown")).stem

    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=str(INDEX_PERSIST_DIR))
    return index


def get_or_build_index() -> VectorStoreIndex:
    return build_index(force_rebuild=False)
