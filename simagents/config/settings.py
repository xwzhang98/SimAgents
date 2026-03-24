"""Configuration system: Pydantic BaseSettings merging YAML + environment variables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.01

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0, got {v}")
        return v


class RAGSettings(BaseModel):
    pdf_loader: str = "unstructured"
    vector_store: str = "chroma"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"


class ExtractionSettings(BaseModel):
    max_iterations: int = 2
    target_software: str = "mp-gadget"


class PathSettings(BaseModel):
    output_dir: str = "./output"
    software_profiles_dir: str = "./data/software_profiles"


class SLURMSettings(BaseModel):
    partition: str = "RM"
    nodes: int = 1
    ntasks: int = 2
    cpus_per_task: int = 14
    time: str = "16:00:00"
    mem_per_cpu: str = "8G"


class Settings(BaseSettings):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    slurm: Optional[SLURMSettings] = None

    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "Settings":
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            return cls()
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_yaml(self, yaml_path: str | Path) -> None:
        """Write settings to a YAML file (excludes API keys)."""
        yaml_path = Path(yaml_path)
        data = {}
        for field_name in ["llm", "rag", "extraction", "paths", "slurm"]:
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value.model_dump()
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
