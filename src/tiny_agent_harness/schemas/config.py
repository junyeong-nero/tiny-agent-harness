from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: str
    supervisor: str | None = None
    planner: str | None = Field(
        default=None,
        validation_alias=AliasChoices("planner", "orchestrator"),
    )
    explorer: str | None = None
    worker: str | None = Field(
        default=None,
        validation_alias=AliasChoices("worker", "executor"),
    )
    reviewer: str | None = None

    @property
    def orchestrator(self) -> str | None:
        return self.planner

    @field_validator(
        "default",
        "supervisor",
        "planner",
        "explorer",
        "worker",
        "reviewer",
        mode="before",
    )
    @classmethod
    def validate_model_name(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("model name must be a non-empty string")
        return value.strip()

    @model_validator(mode="after")
    def apply_defaults(self) -> "ModelsConfig":
        self.supervisor = self.supervisor or self.default
        self.planner = self.planner or self.default
        self.explorer = self.explorer or self.default
        self.worker = self.worker or self.default
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

    supervisor_max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("supervisor_max_retries", "orchestrator_max_retries"),
    )
    planner_max_tool_steps: int = Field(
        default=2,
        validation_alias=AliasChoices("planner_max_tool_steps", "orchestrator_max_tool_steps"),
    )
    explorer_max_tool_steps: int = 3
    worker_max_tool_steps: int = Field(
        default=3,
        validation_alias=AliasChoices("worker_max_tool_steps", "executor_max_tool_steps"),
    )
    reviewer_max_tool_steps: int = 3

    @property
    def orchestrator_max_retries(self) -> int:
        return self.supervisor_max_retries

    @property
    def orchestrator_max_tool_steps(self) -> int:
        return self.planner_max_tool_steps

    @field_validator(
        "supervisor_max_retries",
        "planner_max_tool_steps",
        "explorer_max_tool_steps",
        "worker_max_tool_steps",
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

    supervisor: list[str] = Field(default_factory=list)
    planner: list[str] = Field(
        default_factory=lambda: ["list_files", "search"],
        validation_alias=AliasChoices("planner", "orchestrator"),
    )
    explorer: list[str] = Field(
        default_factory=lambda: ["list_files", "search", "read_file", "git_diff"]
    )
    worker: list[str] = Field(
        default_factory=lambda: ["bash", "read_file", "search", "list_files", "apply_patch"],
        validation_alias=AliasChoices("worker", "executor"),
    )
    reviewer: list[str] = Field(
        default_factory=lambda: ["read_file", "search", "list_files", "git_diff"]
    )

    @property
    def orchestrator(self) -> list[str]:
        return list(self.planner)

    @field_validator("supervisor", "planner", "explorer", "worker", "reviewer", mode="before")
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
        planner_permissions = list(self.planner)
        worker_permissions = list(self.worker)
        return {
            "supervisor": list(self.supervisor),
            "planner": planner_permissions,
            "orchestrator": planner_permissions,
            "explorer": list(self.explorer),
            "worker": worker_permissions,
            "executor": worker_permissions,
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
