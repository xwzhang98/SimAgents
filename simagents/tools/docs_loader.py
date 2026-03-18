"""Software documentation loading and retriever construction."""
from __future__ import annotations
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from simagents.config.settings import RAGSettings
from simagents.tools.pdf_loader import _get_embeddings, _build_vector_store, _get_text_splitter


def build_docs_retriever(target_software: str, rag_settings: RAGSettings, software_docs_dir: str = "./data/software_docs"):
    docs_path = Path(software_docs_dir) / target_software
    if not docs_path.exists() or not any(docs_path.glob("*.md")):
        raise FileNotFoundError(f"No docs found for '{target_software}' at {docs_path}. Add markdown files to {docs_path}/ to support this software.")
    loader = DirectoryLoader(str(docs_path), glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    documents = loader.load()
    splitter = _get_text_splitter(rag_settings)
    chunks = splitter.split_documents(documents)
    embeddings = _get_embeddings(rag_settings)
    vector_store = _build_vector_store(chunks, embeddings, rag_settings.vector_store)
    return vector_store.as_retriever(search_kwargs={"k": 10})
