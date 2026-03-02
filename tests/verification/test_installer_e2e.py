import json
import pathlib
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestInstallerE2E(unittest.TestCase):
    def _run(self, *args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(args), check=False, capture_output=True, text=True, cwd=cwd)

    def test_apply_and_rollback_for_both_profiles(self):
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


if __name__ == "__main__":
    unittest.main()
