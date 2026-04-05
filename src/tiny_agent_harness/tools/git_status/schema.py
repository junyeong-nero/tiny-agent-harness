from pydantic import BaseModel, ConfigDict


class GitStatusArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    porcelain: bool = True
