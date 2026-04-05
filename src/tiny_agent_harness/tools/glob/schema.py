from pydantic import BaseModel, ConfigDict, Field


class GlobArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    path: str = "."
    limit: int = Field(default=200, ge=1)
