from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class SkillResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str
    prompt: str
    ok: bool
    error: str | None = None


class BaseSkill(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def execute(self, args: str) -> SkillResult:
        """args를 받아 harness에 보낼 prompt를 SkillResult로 반환"""
        raise NotImplementedError


__all__ = [
    "BaseSkill",
    "SkillResult",
]
