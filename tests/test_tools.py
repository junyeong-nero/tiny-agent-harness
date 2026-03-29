import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.tools import (
    ApplyPatchTool,
    BashTool,
    GitDiffTool,
    ListFilesTool,
    ReadFileTool,
    SearchTool,
    create_default_tools,
)


class ToolsTestCase(unittest.TestCase):
    def test_create_default_tools_contains_expected_names(self) -> None:
        tools = create_default_tools(str(ROOT_DIR))
        self.assertEqual(
            set(tools),
            {"bash", "read_file", "search", "list_files", "apply_patch", "git_diff"},
        )

    def test_file_tools_read_search_and_list_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            docs_dir = workspace / "docs"
            docs_dir.mkdir()
            sample_file = docs_dir / "note.txt"
            sample_file.write_text("alpha\nbeta keyword\ngamma\n", encoding="utf-8")

            read_tool = ReadFileTool(workspace)
            search_tool = SearchTool(workspace)
            list_files_tool = ListFilesTool(workspace)

            read_result = read_tool.run("docs/note.txt", start_line=2, end_line=2)
            self.assertTrue(read_result.ok)
            self.assertEqual(read_result.content, "beta keyword")

            search_result = search_tool.run("keyword")
            self.assertTrue(search_result.ok)
            self.assertIn("docs/note.txt:2:beta keyword", search_result.content)

            list_result = list_files_tool.run()
            self.assertTrue(list_result.ok)
            self.assertIn("docs/note.txt", list_result.content)

    def test_bash_tool_runs_in_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            bash_tool = BashTool(workspace)

            result = bash_tool.run("pwd")

            self.assertTrue(result.ok)
            self.assertEqual(Path(result.content.strip()).resolve(), workspace.resolve())

    def test_apply_patch_and_git_diff_tools_work_on_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
            target_file = workspace / "demo.txt"
            target_file.write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "demo.txt"], cwd=workspace, check=True, capture_output=True)

            apply_patch_tool = ApplyPatchTool(workspace)
            git_diff_tool = GitDiffTool(workspace)

            patch = (
                "diff --git a/demo.txt b/demo.txt\n"
                "--- a/demo.txt\n"
                "+++ b/demo.txt\n"
                "@@ -1 +1 @@\n"
                "-before\n"
                "+after\n"
            )

            apply_result = apply_patch_tool.run(patch)
            self.assertTrue(apply_result.ok, apply_result.error)
            self.assertEqual(target_file.read_text(encoding="utf-8"), "after\n")

            diff_result = git_diff_tool.run(paths=["demo.txt"])
            self.assertTrue(diff_result.ok)
            self.assertIn("+after", diff_result.content)


if __name__ == "__main__":
    unittest.main()
