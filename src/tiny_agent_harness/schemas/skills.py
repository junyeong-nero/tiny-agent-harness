from pydantic import BaseModel, ConfigDict


class SkillResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str
    prompt: str
    ok: bool
    error: str | None = None
