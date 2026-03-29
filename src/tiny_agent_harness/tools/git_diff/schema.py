from pydantic import BaseModel, ConfigDict, Field


class GitDiffArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(default_factory=list)
    staged: bool = False
