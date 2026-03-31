from abc import ABC, abstractmethod

from tiny_agent_harness.schemas import SkillResult


class BaseSkill(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def execute(self, args: str) -> SkillResult:
        """args를 받아 harness에 보낼 prompt를 SkillResult로 반환"""
        raise NotImplementedError


__all__ = [
    "BaseSkill",
]
