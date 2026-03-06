import json
import pathlib
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestTemplateGolden(unittest.TestCase):
    def test_generated_templates_match_golden(self):
        intent_fixture = REPO_ROOT / "tests" / "verification" / "fixtures" / "intents" / "pre-commit-sync-loc.json"
        web_intent_fixture = REPO_ROOT / "tests" / "verification" / "fixtures" / "intents" / "web-frontend-skill.json"
        codex_golden = REPO_ROOT / "tests" / "verification" / "fixtures" / "golden" / "codex_AGENTS.md"
        claude_golden = REPO_ROOT / "tests" / "verification" / "fixtures" / "golden" / "claude_settings.json"

        self.assertTrue(intent_fixture.exists(), msg=f"Missing fixture: {intent_fixture}")
        self.assertTrue(web_intent_fixture.exists(), msg=f"Missing fixture: {web_intent_fixture}")
        self.assertTrue(codex_golden.exists(), msg=f"Missing fixture: {codex_golden}")
        self.assertTrue(claude_golden.exists(), msg=f"Missing fixture: {claude_golden}")

        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "project"
            subprocess.run(["cp", "-R", str(REPO_ROOT), str(project)], check=True)

            cmd = [
                "python3",
                str(REPO_ROOT / "common" / "install" / "scripts" / "portable_generate_templates.py"),
                "--repo-root",
                str(project),
                "--intent-file",
                str(intent_fixture),
            ]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            got_codex = (project / "ios" / "codex" / "AGENTS.md").read_text(encoding="utf-8")
            exp_codex = codex_golden.read_text(encoding="utf-8")
            self.assertEqual(got_codex, exp_codex)

            got_claude = json.loads((project / "ios" / "claude" / "settings.json").read_text(encoding="utf-8"))
            exp_claude = json.loads(claude_golden.read_text(encoding="utf-8"))
            self.assertEqual(got_claude, exp_claude)

            web_cmd = [
                "python3",
                str(REPO_ROOT / "common" / "install" / "scripts" / "portable_generate_templates.py"),
                "--repo-root",
                str(project),
                "--intent-file",
                str(web_intent_fixture),
            ]
            web_result = subprocess.run(web_cmd, check=False, capture_output=True, text=True)
            self.assertEqual(web_result.returncode, 0, msg=web_result.stderr)
            self.assertTrue((project / "web" / "codex" / "AGENTS.md").exists())
            self.assertTrue((project / "web" / "claude" / "CLAUDE.md").exists())
            web_codex = (project / "web" / "codex" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("frontend-design", web_codex)


if __name__ == "__main__":
    unittest.main()
