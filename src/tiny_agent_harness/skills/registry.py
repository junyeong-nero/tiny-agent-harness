from tiny_agent_harness.schemas import SkillResult
from tiny_agent_harness.skills.base import BaseSkill

SkillRegistry = dict[str, BaseSkill]


class SkillRunner:
    def __init__(self, skills: SkillRegistry) -> None:
        self._skills = skills

    def run(self, name: str, args: str) -> SkillResult | None:
        """스킬을 실행합니다. 등록되지 않은 스킬이면 None을 반환합니다."""
        skill = self._skills.get(name)
        if skill is None:
            return None
        try:
            return skill.execute(args)
        except Exception as exc:
            return SkillResult(
                skill=name,
                prompt="",
                ok=False,
                error=str(exc),
            )

    def available_names(self) -> list[str]:
        return list(self._skills.keys())

    def available_skills(self) -> list[tuple[str, str]]:
        """Returns (name, description) pairs for all registered skills."""
        return [(s.name, s.description) for s in self._skills.values()]


__all__ = [
    "SkillRegistry",
    "SkillRunner",
]
