from pydantic import BaseModel, ConfigDict


class ListFilesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = "."
    glob_pattern: str | None = None
