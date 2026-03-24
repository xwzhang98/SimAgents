"""Tests for software docs loading and retriever construction."""
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from simagents.tools.docs_loader import build_docs_retriever
from simagents.config.settings import RAGSettings


def test_build_docs_retriever_loads_markdown_files(tmp_path):
    docs_dir = tmp_path / "mp-gadget-docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "param_ref.md").write_text("# Params\nBoxSize: kpc/h")
    (docs_dir / "genic_ref.md").write_text("# GenIC\nNgrid: particle count")
    with patch("simagents.tools.docs_loader._get_embeddings") as mock_emb:
        with patch("simagents.tools.docs_loader._build_vector_store") as mock_vs:
            mock_retriever = MagicMock()
            mock_vs.return_value.as_retriever.return_value = mock_retriever
            rag_settings = RAGSettings()
            retriever = build_docs_retriever(docs_dir, rag_settings)
            assert retriever == mock_retriever
            call_args = mock_vs.call_args
            docs = call_args[0][0]
            assert len(docs) >= 2


def test_build_docs_retriever_unknown_software_raises(tmp_path):
    docs_dir = tmp_path / "nonexistent_docs"
    with pytest.raises(FileNotFoundError, match="No docs found"):
        build_docs_retriever(docs_dir, RAGSettings())
