from pydantic import BaseModel, ConfigDict


class ReadFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    start_line: int | None = None
    end_line: int | None = None
