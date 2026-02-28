import json
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import tomllib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "common" / "install" / "scripts"
MODULE_PATH = SCRIPTS_DIR / "portable_config.py"
SPEC = importlib.util.spec_from_file_location("portable_config_impl", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module: {MODULE_PATH}")
PORTABLE_CONFIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PORTABLE_CONFIG)
load_profile_and_manifest = PORTABLE_CONFIG.load_profile_and_manifest


class TestPortableApply(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = pathlib.Path(self.tmp.name) / "demo-project"
        self.project_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_apply(self, extra_args=None):
        script = REPO_ROOT / "common" / "install" / "scripts" / "portable_apply.py"
        args = [
            "python3",
            str(script),
            "--project-root",
            str(self.project_root),
            "--template-root",
            str(REPO_ROOT),
            "--profile",
            "codex-ios",
            "--namespace",
            "super-dev",
        ]
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(args, check=False, capture_output=True, text=True)

    def test_profile_and_manifest_load_successfully(self):
        profile, manifest = load_profile_and_manifest(REPO_ROOT, "codex-ios")
        self.assertEqual(profile["profile"], "codex-ios")
        self.assertEqual(manifest["profile"], "codex-ios")
        self.assertGreaterEqual(len(manifest["actions"]), 3)

    def test_apply_creates_transaction_state_and_files(self):
        result = self._run_apply()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        state_path = self.project_root / ".codex" / "portable" / "state.json"
        self.assertTrue(state_path.exists())

        agents_path = self.project_root / "AGENTS.md"
        self.assertTrue(agents_path.exists())
        agents_text = agents_path.read_text(encoding="utf-8")
        self.assertIn("BEGIN SUPER-DEV MANAGED BLOCK", agents_text)

        codex_config = self.project_root / ".codex" / "config.toml"
        self.assertTrue(codex_config.exists())

        skill_file = (
            self.project_root
            / ".agents"
            / "skills"
            / "super-dev"
            / "xcode-builder"
            / "SKILL.md"
        )
        self.assertTrue(skill_file.exists())

        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertIn("transactions", state)
        self.assertEqual(len(state["transactions"]), 1)

    def test_apply_preserves_existing_user_toml_values(self):
        config_path = self.project_root / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            'model = "custom-model"\n\n[features]\nmulti_agent = false\n',
            encoding="utf-8",
        )

        result = self._run_apply()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        merged = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(merged["model"], "custom-model")
        self.assertEqual(merged["features"]["multi_agent"], False)
        self.assertIn("mcp_servers", merged)


if __name__ == "__main__":
    unittest.main()
