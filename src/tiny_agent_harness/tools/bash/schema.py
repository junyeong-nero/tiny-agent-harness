from pydantic import BaseModel, ConfigDict


class BashArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    timeout_seconds: int = 60
