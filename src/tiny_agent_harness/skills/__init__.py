from tiny_agent_harness.skills.base import BaseSkill, SkillResult
from tiny_agent_harness.skills.commit import CommitSkill
from tiny_agent_harness.skills.registry import SkillRegistry, SkillRunner


def create_default_skills() -> SkillRegistry:
    skills: list[BaseSkill] = [
        CommitSkill(),
    ]
    return {s.name: s for s in skills}


__all__ = [
    "BaseSkill",
    "CommitSkill",
    "SkillRegistry",
    "SkillResult",
    "SkillRunner",
    "create_default_skills",
]
