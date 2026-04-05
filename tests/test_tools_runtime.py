from pathlib import Path
import subprocess

from tiny_agent_harness.schemas import ToolPermissionsConfig
from tiny_agent_harness.tools import create_default_tools


class TestGlobTool:
    def test_returns_matching_files_for_glob_pattern(self, tmp_path: Path):
        tool = create_default_tools(str(tmp_path))["glob"]
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("print('hi')\n", encoding="utf-8")
        (src_dir / "util.py").write_text("print('util')\n", encoding="utf-8")
        (src_dir / "notes.txt").write_text("notes\n", encoding="utf-8")

        result = tool.run({"path": "src", "pattern": "*.py"})

        assert result.ok is True
        assert result.content.splitlines() == ["src/app.py", "src/util.py"]
        assert result.metadata["match_count"] == 2


class TestReplaceInFileTool:
    def test_replaces_exact_text_when_expected_occurrence_matches(self, tmp_path: Path):
        tool = create_default_tools(str(tmp_path))["replace_in_file"]
        target = tmp_path / "example.txt"
        target.write_text("alpha\nbeta\n", encoding="utf-8")

        result = tool.run(
            {
                "path": "example.txt",
                "old_text": "beta",
                "new_text": "gamma",
            }
        )

        assert result.ok is True
        assert target.read_text(encoding="utf-8") == "alpha\ngamma\n"
        assert result.metadata["replacements"] == 1

    def test_fails_when_occurrence_count_does_not_match(self, tmp_path: Path):
        tool = create_default_tools(str(tmp_path))["replace_in_file"]
        target = tmp_path / "example.txt"
        target.write_text("same\nsame\n", encoding="utf-8")

        result = tool.run(
            {
                "path": "example.txt",
                "old_text": "same",
                "new_text": "different",
            }
        )

        assert result.ok is False
        assert result.metadata["occurrence_count"] == 2
        assert target.read_text(encoding="utf-8") == "same\nsame\n"


class TestGitStatusTool:
    def test_returns_porcelain_status_output(self, tmp_path: Path):
        tool = create_default_tools(str(tmp_path))["git_status"]
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
        tracked = tmp_path / "tracked.txt"
        tracked.write_text("content\n", encoding="utf-8")

        result = tool.run({})

        assert result.ok is True
        assert "?? tracked.txt" in result.content


def test_create_default_tools_includes_new_tools(tmp_path: Path):
    tools = create_default_tools(str(tmp_path))

    assert {"glob", "replace_in_file", "git_status"}.issubset(tools.keys())


def test_default_tool_permissions_include_new_tools():
    permissions = ToolPermissionsConfig()
    data = permissions.model_dump()

    assert "glob" in data["planner"]
    assert "glob" in data["explorer"]
    assert "replace_in_file" in data["worker"]
    assert "search" not in data["worker"]
    assert "glob" not in data["worker"]
    assert "list_files" not in data["worker"]
    assert "git_status" in data["explorer"]
    assert "git_status" in data["worker"]
    assert "git_status" in data["verifier"]
