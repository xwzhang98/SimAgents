"""Tests for PDF loading and retriever construction."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from simagents.tools.pdf_loader import get_pdf_loader, build_paper_retriever
from simagents.config.settings import RAGSettings


def test_get_pdf_loader_pypdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        loader = get_pdf_loader(f.name, "pypdf")
        assert loader is not None


def test_get_pdf_loader_invalid_raises():
    with pytest.raises(ValueError, match="Unknown PDF loader"):
        get_pdf_loader("/fake.pdf", "nonexistent_loader")


def test_build_paper_retriever_returns_retriever():
    mock_docs = [MagicMock(page_content="BoxSize is 100 Mpc/h", metadata={"page": 1})]
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    with patch("simagents.tools.pdf_loader.get_pdf_loader") as mock_loader_fn:
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_docs
        mock_loader_fn.return_value = mock_loader
        with patch("simagents.tools.pdf_loader._get_text_splitter") as mock_splitter_fn:
            mock_splitter = MagicMock()
            mock_splitter.split_documents.return_value = mock_docs
            mock_splitter_fn.return_value = mock_splitter
            with patch("simagents.tools.pdf_loader._get_embeddings") as mock_emb_fn:
                mock_emb_fn.return_value = MagicMock()
                with patch("simagents.tools.pdf_loader._build_vector_store") as mock_vs:
                    mock_retriever = MagicMock()
                    mock_vs.return_value.as_retriever.return_value = mock_retriever
                    rag_settings = RAGSettings()
                    retriever = build_paper_retriever(tmp_path, rag_settings)
                    assert retriever == mock_retriever
