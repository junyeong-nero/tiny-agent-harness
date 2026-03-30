from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: str
    orchestrator: str | None = None
    executor: str | None = None
    reviewer: str | None = None

    @field_validator("default", "orchestrator", "executor", "reviewer", mode="before")
    @classmethod
    def validate_model_name(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("model name must be a non-empty string")
        return value.strip()

    @model_validator(mode="after")
    def apply_defaults(self) -> "ModelsConfig":
        self.orchestrator = self.orchestrator or self.default
        self.executor = self.executor or self.default
        self.reviewer = self.reviewer or self.default
        return self


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: int = 2

    @field_validator("max_retries", mode="before")
    @classmethod
    def validate_max_retries(cls, value: Any) -> int:
        if not isinstance(value, int) or value < 0:
            raise ValueError("max_retries must be an integer greater than or equal to 0")
        return value


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orchestrator_max_retries: int = 3
    orchestrator_max_tool_steps: int = 2
    executor_max_tool_steps: int = 3
    reviewer_max_tool_steps: int = 3

    @field_validator(
        "orchestrator_max_retries",
        "orchestrator_max_tool_steps",
        "executor_max_tool_steps",
        "reviewer_max_tool_steps",
        mode="before",
    )
    @classmethod
    def validate_max_steps(cls, value: Any) -> int:
        if not isinstance(value, int) or value < 1:
            raise ValueError("value must be an integer greater than or equal to 1")
        return value


class ToolPermissionsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orchestrator: list[str] = Field(default_factory=lambda: ["list_files", "search"])
    executor: list[str] = Field(
        default_factory=lambda: ["bash", "read_file", "search", "list_files", "apply_patch"]
    )
    reviewer: list[str] = Field(
        default_factory=lambda: ["read_file", "search", "list_files", "git_diff"]
    )

    @field_validator("orchestrator", "executor", "reviewer", mode="before")
    @classmethod
    def validate_permissions(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("tool permissions must be a list of tool names")

        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("tool permission entries must be non-empty strings")
            normalized.append(item.strip())
        return normalized

    def as_actor_permissions(self) -> dict[str, list[str]]:
        return {
            "orchestrator": list(self.orchestrator),
            "executor": list(self.executor),
            "reviewer": list(self.reviewer),
        }


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    models: ModelsConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    tools: ToolPermissionsConfig = Field(default_factory=ToolPermissionsConfig)

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provider must be a non-empty string")
        return value.strip()


def _load_raw_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        with files("tiny_agent_harness").joinpath("default_config.yaml").open(
            "r", encoding="utf-8"
        ) as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError("config root must be a mapping")
        return raw

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("config root must be a mapping")
    return raw


def load_config(path: str | Path | None = None) -> AppConfig:
    raw = _load_raw_config(path)

    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"invalid config: {exc}") from exc
