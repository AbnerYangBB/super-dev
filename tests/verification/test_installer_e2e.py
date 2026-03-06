import json
import pathlib
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestInstallerE2E(unittest.TestCase):
    def _run(self, *args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(args), check=False, capture_output=True, text=True, cwd=cwd)

    def test_apply_and_rollback_for_all_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "demo"
            project.mkdir(parents=True, exist_ok=True)

            apply_script = REPO_ROOT / "common" / "install" / "scripts" / "portable_apply.py"
            rollback_script = REPO_ROOT / "common" / "install" / "scripts" / "portable_rollback.py"

            codex_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "codex-ios",
                "--namespace",
                "super-dev",
            )
            self.assertEqual(codex_apply.returncode, 0, msg=codex_apply.stderr)
            codex_payload = json.loads(codex_apply.stdout)
            self.assertEqual(codex_payload["status"], "ok")

            codex_rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(codex_rollback.returncode, 0, msg=codex_rollback.stderr)

            claude_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "claude-ios",
                "--namespace",
                "super-dev",
            )
            self.assertEqual(claude_apply.returncode, 0, msg=claude_apply.stderr)
            claude_payload = json.loads(claude_apply.stdout)
            self.assertEqual(claude_payload["status"], "ok")

            claude_rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(claude_rollback.returncode, 0, msg=claude_rollback.stderr)

            trae_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "trae-ios",
                "--namespace",
                "super-dev",
            )
            self.assertEqual(trae_apply.returncode, 0, msg=trae_apply.stderr)
            trae_payload = json.loads(trae_apply.stdout)
            self.assertEqual(trae_payload["status"], "ok")

            trae_rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(trae_rollback.returncode, 0, msg=trae_rollback.stderr)

            codex_web_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "codex-web",
                "--namespace",
                "super-dev-web",
            )
            self.assertEqual(codex_web_apply.returncode, 0, msg=codex_web_apply.stderr)
            self.assertEqual(json.loads(codex_web_apply.stdout)["status"], "ok")

            codex_web_rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(codex_web_rollback.returncode, 0, msg=codex_web_rollback.stderr)

            claude_web_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "claude-web",
                "--namespace",
                "super-dev-web",
            )
            self.assertEqual(claude_web_apply.returncode, 0, msg=claude_web_apply.stderr)
            self.assertEqual(json.loads(claude_web_apply.stdout)["status"], "ok")

            claude_web_rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(claude_web_rollback.returncode, 0, msg=claude_web_rollback.stderr)

            trae_web_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "trae-web",
                "--namespace",
                "super-dev-web",
            )
            self.assertEqual(trae_web_apply.returncode, 0, msg=trae_web_apply.stderr)
            self.assertEqual(json.loads(trae_web_apply.stdout)["status"], "ok")

            trae_web_rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(trae_web_rollback.returncode, 0, msg=trae_web_rollback.stderr)

    def test_codex_ios_and_web_can_coexist_in_same_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp) / "demo"
            project.mkdir(parents=True, exist_ok=True)

            apply_script = REPO_ROOT / "common" / "install" / "scripts" / "portable_apply.py"
            rollback_script = REPO_ROOT / "common" / "install" / "scripts" / "portable_rollback.py"

            codex_ios_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "codex-ios",
                "--namespace",
                "super-dev-ios",
            )
            self.assertEqual(codex_ios_apply.returncode, 0, msg=codex_ios_apply.stderr)

            codex_web_apply = self._run(
                "python3",
                str(apply_script),
                "--project-root",
                str(project),
                "--template-root",
                str(REPO_ROOT),
                "--profile",
                "codex-web",
                "--namespace",
                "super-dev-web",
            )
            self.assertEqual(codex_web_apply.returncode, 0, msg=codex_web_apply.stderr)

            agents_text = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("xcode-builder", agents_text)
            self.assertIn("frontend-design", agents_text)
            self.assertTrue((project / ".agents" / "skills" / "super-dev-ios").exists())
            self.assertTrue((project / ".agents" / "skills" / "super-dev-web").exists())

            rollback = self._run(
                "python3",
                str(rollback_script),
                "--project-root",
                str(project),
            )
            self.assertEqual(rollback.returncode, 0, msg=rollback.stderr)

            agents_after_rollback = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("xcode-builder", agents_after_rollback)
            self.assertNotIn("frontend-design", agents_after_rollback)
            self.assertTrue((project / ".agents" / "skills" / "super-dev-ios").exists())
            self.assertFalse((project / ".agents" / "skills" / "super-dev-web").exists())


if __name__ == "__main__":
    unittest.main()
