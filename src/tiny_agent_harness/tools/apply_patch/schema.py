from pydantic import BaseModel, ConfigDict


class ApplyPatchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch: str
