import json
import pathlib
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestTemplateGeneration(unittest.TestCase):
    def _run_generate(self, repo_root: pathlib.Path, intent_path: pathlib.Path):
        script = REPO_ROOT / "common" / "install" / "scripts" / "portable_generate_templates.py"
        args = [
            "python3",
            str(script),
            "--repo-root",
            str(repo_root),
            "--intent-file",
            str(intent_path),
        ]
        return subprocess.run(args, check=False, capture_output=True, text=True)

    def test_generate_updates_codex_and_claude_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = pathlib.Path(tmp)
            project = tmp_root / "project"

            # Copy only needed files/directories for generator execution.
            subprocess.run(["cp", "-R", str(REPO_ROOT), str(project)], check=True)

            intent = project / "common" / "platforms" / "intents" / "examples" / "pre-commit-sync-loc.json"
            result = self._run_generate(project, intent)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            codex_agents = (project / "ios" / "codex" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("sync-add-ios-loc", codex_agents)

            claude_settings = json.loads((project / "ios" / "claude" / "settings.json").read_text(encoding="utf-8"))
            pre_tool_use = claude_settings.get("hooks", {}).get("PreToolUse", [])
            self.assertTrue(pre_tool_use, msg="Expected PreToolUse hook in claude settings")
            hook_cmd = pre_tool_use[0]["hooks"][0]["command"]
            self.assertIn("sync-add-ios-loc", hook_cmd)


if __name__ == "__main__":
    unittest.main()
