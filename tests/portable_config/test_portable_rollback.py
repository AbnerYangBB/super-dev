import json
import pathlib
import subprocess
import tempfile
import tomllib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestPortableRollback(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = pathlib.Path(self.tmp.name) / "demo-project"
        self.project_root.mkdir(parents=True, exist_ok=True)

        self.original_agents = "# Existing\n\nUser content\n"
        (self.project_root / "AGENTS.md").write_text(
            self.original_agents,
            encoding="utf-8",
        )

        config_path = self.project_root / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('model = "custom-model"\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_apply(self, profile="codex-ios"):
        script = REPO_ROOT / "common" / "install" / "scripts" / "portable_apply.py"
        args = [
            "python3",
            str(script),
            "--project-root",
            str(self.project_root),
            "--template-root",
            str(REPO_ROOT),
            "--profile",
            profile,
            "--namespace",
            "super-dev",
        ]
        return subprocess.run(args, check=False, capture_output=True, text=True)

    def _run_rollback(self):
        script = REPO_ROOT / "common" / "install" / "scripts" / "portable_rollback.py"
        args = [
            "python3",
            str(script),
            "--project-root",
            str(self.project_root),
        ]
        return subprocess.run(args, check=False, capture_output=True, text=True)

    def test_rollback_restores_previous_files_and_removes_created_files(self):
        apply_result = self._run_apply()
        self.assertEqual(apply_result.returncode, 0, msg=apply_result.stderr)

        rollback_result = self._run_rollback()
        self.assertEqual(rollback_result.returncode, 0, msg=rollback_result.stderr)

        agents_text = (self.project_root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(agents_text, self.original_agents)

        config_text = (self.project_root / ".codex" / "config.toml").read_text(encoding="utf-8")
        merged = tomllib.loads(config_text)
        self.assertEqual(merged["model"], "custom-model")

        copied_skill = (
            self.project_root
            / ".agents"
            / "skills"
            / "super-dev"
            / "xcode-builder"
            / "SKILL.md"
        )
        self.assertFalse(copied_skill.exists())

        state_path = self.project_root / ".codex" / "portable" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertTrue(state["transactions"][0]["rolled_back"])

    def test_rollback_claude_apply_uses_claude_state(self):
        apply_result = self._run_apply(profile="claude-ios")
        self.assertEqual(apply_result.returncode, 0, msg=apply_result.stderr)

        claude_state_path = self.project_root / ".claude" / "portable" / "state.json"
        self.assertTrue(claude_state_path.exists())
        self.assertFalse((self.project_root / ".codex" / "portable").exists())

        rollback_result = self._run_rollback()
        self.assertEqual(rollback_result.returncode, 0, msg=rollback_result.stderr)
        payload = json.loads(rollback_result.stdout)
        self.assertEqual(payload["state_file"], ".claude/portable/state.json")

        state = json.loads(claude_state_path.read_text(encoding="utf-8"))
        self.assertTrue(state["transactions"][0]["rolled_back"])

        claude_skill = (
            self.project_root
            / ".claude"
            / "skills"
            / "super-dev"
            / "xcode-builder"
            / "SKILL.md"
        )
        self.assertFalse(claude_skill.exists())


if __name__ == "__main__":
    unittest.main()
