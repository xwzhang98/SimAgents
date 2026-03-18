"""Tests for the configuration system."""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from simagents.config.settings import Settings, LLMSettings, RAGSettings, ExtractionSettings


def test_default_settings():
    settings = Settings()
    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4o"
    assert settings.llm.temperature == 0.01
    assert settings.rag.vector_store == "chroma"
    assert settings.rag.pdf_loader == "unstructured"
    assert settings.rag.chunk_size == 1000
    assert settings.extraction.max_iterations == 2
    assert settings.extraction.target_software == "mp-gadget"


def test_settings_from_yaml():
    yaml_content = {
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temperature": 0.1},
        "rag": {"vector_store": "faiss", "chunk_size": 500},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(yaml_content, f)
        yaml_path = f.name

    try:
        settings = Settings.from_yaml(yaml_path)
        assert settings.llm.provider == "anthropic"
        assert settings.llm.model == "claude-sonnet-4-20250514"
        assert settings.rag.vector_store == "faiss"
        assert settings.rag.chunk_size == 500
        assert settings.rag.chunk_overlap == 200
    finally:
        os.unlink(yaml_path)


def test_settings_env_vars_for_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-456")
    settings = Settings()
    assert settings.openai_api_key == "sk-test-123"
    assert settings.anthropic_api_key == "sk-ant-test-456"


def test_settings_missing_yaml_uses_defaults():
    settings = Settings.from_yaml("/nonexistent/path.yaml")
    assert settings.llm.provider == "openai"


def test_llm_settings_validation():
    with pytest.raises(ValueError):
        LLMSettings(provider="openai", model="gpt-4o", temperature=3.0)
