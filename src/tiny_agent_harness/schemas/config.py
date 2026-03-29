from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator


class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: str
    main_loop: str | None = None
    executor: str | None = None
    reviewer: str | None = None

    @field_validator("default", "main_loop", "executor", "reviewer", mode="before")
    @classmethod
    def validate_model_name(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("model name must be a non-empty string")
        return value.strip()

    @model_validator(mode="after")
    def apply_defaults(self) -> "ModelsConfig":
        self.main_loop = self.main_loop or self.default
        self.executor = self.executor or self.default
        self.reviewer = self.reviewer or self.default
        return self


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    models: ModelsConfig

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider must be a non-empty string")
        return value.strip()


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("config root must be a mapping")

    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"invalid config: {exc}") from exc
