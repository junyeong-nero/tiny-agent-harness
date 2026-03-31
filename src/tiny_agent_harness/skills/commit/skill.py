from tiny_agent_harness.schemas import SkillResult
from tiny_agent_harness.skills.base import BaseSkill

_PROMPT = """\
Split changes into logical commits.

Instructions:
- Run `git diff --staged` to see what's staged
- If nothing is staged, run `git diff` to check for unstaged changes
  - If unstaged changes exist, run `git add -A` to stage everything, then proceed
  - If there are no changes at all, inform the user and stop
- Group related changes into separate commits
- Use conventional commit format with bracketed tags: [feat], [fix], [refactor], [docs], [test], [chore]
- Write concise, descriptive commit messages in English
- Commit each group separately with `git commit -m "..."`
- Do NOT push

{extra}
""".strip()


class CommitSkill(BaseSkill):
    name = "commit"
    description = "Split staged changes into logical commits with conventional tags"

    def execute(self, args: str) -> SkillResult:
        extra = f"Additional instructions: {args.strip()}" if args.strip() else ""
        return SkillResult(
            skill=self.name,
            prompt=_PROMPT.format(extra=extra).strip(),
            ok=True,
        )


__all__ = ["CommitSkill"]
