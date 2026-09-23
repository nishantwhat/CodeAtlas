"""Centralized configuration loader using Pydantic."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AnalysisConfig(BaseModel):
    clang_library_path: str | None = None
    default_c_standard: str = "c11"
    default_cpp_standard: str = "c++17"


class AppConfig(BaseModel):
    env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)


def load_config(config_path: Path | str | None = None) -> AppConfig:
    """Load configuration from YAML file or return defaults."""
    if config_path is None:
        config_path = Path("configs/default_config.yaml")

    path = Path(config_path)
    if not path.is_file():
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    return AppConfig(**data)