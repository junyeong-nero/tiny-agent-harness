from pydantic import BaseModel, ConfigDict


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str
    path: str = "."
