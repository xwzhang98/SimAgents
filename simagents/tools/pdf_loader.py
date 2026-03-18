"""Configurable PDF loading, chunking, and retriever construction."""
from __future__ import annotations
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from simagents.config.settings import RAGSettings


def get_pdf_loader(path: str, loader_type: str):
    if loader_type == "unstructured":
        from langchain_unstructured import UnstructuredLoader
        return UnstructuredLoader(path)
    elif loader_type == "pymupdf":
        from langchain_community.document_loaders import PyMuPDFLoader
        return PyMuPDFLoader(path)
    elif loader_type == "pypdf":
        from langchain_community.document_loaders import PyPDFLoader
        return PyPDFLoader(path)
    elif loader_type == "docling":
        from langchain_docling import DoclingLoader
        return DoclingLoader(path)
    else:
        raise ValueError(f"Unknown PDF loader: '{loader_type}'. Supported: unstructured, pymupdf, pypdf, docling")


def _get_text_splitter(rag_settings: RAGSettings) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(chunk_size=rag_settings.chunk_size, chunk_overlap=rag_settings.chunk_overlap)


def _get_embeddings(rag_settings: RAGSettings):
    if rag_settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=rag_settings.embedding_model)
    elif rag_settings.embedding_provider == "huggingface":
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=rag_settings.embedding_model)
    else:
        raise ValueError(f"Unknown embedding provider: '{rag_settings.embedding_provider}'. Supported: openai, huggingface")


def _build_vector_store(documents, embeddings, store_type: str):
    if store_type == "chroma":
        from langchain_chroma import Chroma
        return Chroma.from_documents(documents, embeddings)
    elif store_type == "faiss":
        from langchain_community.vectorstores import FAISS
        return FAISS.from_documents(documents, embeddings)
    else:
        raise ValueError(f"Unknown vector store: '{store_type}'. Supported: chroma, faiss")


def build_paper_retriever(paper_path: str, rag_settings: RAGSettings):
    path = Path(paper_path)
    if not path.exists():
        raise FileNotFoundError(f"Paper not found: {paper_path}")
    try:
        loader = get_pdf_loader(str(path), rag_settings.pdf_loader)
        documents = loader.load()
    except Exception as e:
        raise RuntimeError(f"Failed to load PDF with '{rag_settings.pdf_loader}' loader: {e}. Try a different loader via config.yaml (rag.pdf_loader).") from e
    splitter = _get_text_splitter(rag_settings)
    chunks = splitter.split_documents(documents)
    embeddings = _get_embeddings(rag_settings)
    vector_store = _build_vector_store(chunks, embeddings, rag_settings.vector_store)
    return vector_store.as_retriever()
