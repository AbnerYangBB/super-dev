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
apply_profile = PORTABLE_CONFIG.apply_profile
PortableConfigError = PORTABLE_CONFIG.PortableConfigError


class TestPortableApply(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = pathlib.Path(self.tmp.name) / "demo-project"
        self.project_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_apply(self, profile="codex-ios", namespace="super-dev", extra_args=None):
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
            namespace,
        ]
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(args, check=False, capture_output=True, text=True)

    def test_profile_and_manifest_load_successfully(self):
        codex_profile, codex_manifest = load_profile_and_manifest(REPO_ROOT, "codex-ios")
        self.assertEqual(codex_profile["profile"], "codex-ios")
        self.assertEqual(codex_manifest["profile"], "codex-ios")
        self.assertGreaterEqual(len(codex_manifest["actions"]), 3)

        claude_profile, claude_manifest = load_profile_and_manifest(REPO_ROOT, "claude-ios")
        self.assertEqual(claude_profile["profile"], "claude-ios")
        self.assertEqual(claude_manifest["profile"], "claude-ios")
        self.assertGreaterEqual(len(claude_manifest["actions"]), 2)

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

    def test_apply_claude_profile_creates_files_and_merges_existing_json_settings(self):
        settings_path = self.project_root / ".claude" / "settings.json"
        mcp_path = self.project_root / ".mcp.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": ["Bash(xcodebuild *)"],
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        mcp_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "custom-server": {
                            "type": "stdio",
                            "command": "custom-mcp",
                            "args": [],
                        }
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self._run_apply(profile="claude-ios")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["conflicts"], 0)

        claude_md = self.project_root / "CLAUDE.md"
        self.assertTrue(claude_md.exists())
        claude_text = claude_md.read_text(encoding="utf-8")
        self.assertIn("BEGIN SUPER-DEV MANAGED BLOCK", claude_text)

        merged = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(merged["permissions"]["allow"], ["Bash(xcodebuild *)"])
        self.assertIn("deny", merged["permissions"])

        mcp_merged = json.loads(mcp_path.read_text(encoding="utf-8"))
        self.assertIn("custom-server", mcp_merged["mcpServers"])
        self.assertIn("sequential-thinking", mcp_merged["mcpServers"])
        self.assertIn("context7", mcp_merged["mcpServers"])
        self.assertIn("serena", mcp_merged["mcpServers"])

        claude_skill = (
            self.project_root
            / ".claude"
            / "skills"
            / "super-dev"
            / "xcode-builder"
            / "SKILL.md"
        )
        self.assertTrue(claude_skill.exists())

    def test_apply_claude_profile_records_conflict_for_invalid_existing_json(self):
        settings_path = self.project_root / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{invalid-json", encoding="utf-8")

        result = self._run_apply(profile="claude-ios")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["conflicts"], 1)
        self.assertEqual(settings_path.read_text(encoding="utf-8"), "{invalid-json")

        state_path = self.project_root / ".codex" / "portable" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        txn = state["transactions"][0]
        self.assertEqual(txn["profile"], "claude-ios")
        self.assertEqual(txn["conflicts"][0]["path"], ".claude/settings.json")
        self.assertEqual(txn["conflicts"][0]["reason"], "target_json_invalid")

    def test_apply_failure_rolls_back_partial_changes(self):
        original_agents = "# Existing AGENTS\n\nUser content\n"
        agents_path = self.project_root / "AGENTS.md"
        agents_path.write_text(original_agents, encoding="utf-8")

        failing_template_root = pathlib.Path(self.tmp.name) / "failing-template"
        profile_dir = failing_template_root / "common" / "install" / "profiles"
        manifest_dir = failing_template_root / "common" / "install" / "manifests"
        source_dir = failing_template_root / "ios" / "codex"
        profile_dir.mkdir(parents=True, exist_ok=True)
        manifest_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)

        (source_dir / "AGENTS.md").write_text("# Managed AGENTS block\n", encoding="utf-8")

        (profile_dir / "failing.json").write_text(
            json.dumps(
                {
                    "profile": "failing",
                    "targets": {
                        "agents": "AGENTS.md",
                        "codex_config": ".codex/config.toml",
                    },
                    "state": {
                        "state_file": ".codex/portable/state.json",
                        "backup_dir": ".codex/portable/backups",
                        "history_dir": ".codex/portable/history",
                        "conflicts_dir": ".codex/portable/conflicts",
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        (manifest_dir / "failing.json").write_text(
            json.dumps(
                {
                    "profile": "failing",
                    "actions": [
                        {
                            "id": "agents",
                            "src": "ios/codex/AGENTS.md",
                            "target": "agents",
                            "strategy": "append_block",
                        },
                        {
                            "id": "broken-config",
                            "src": "ios/codex/missing.toml",
                            "target": "codex_config",
                            "strategy": "merge_toml_keys",
                        },
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(PortableConfigError):
            apply_profile(
                project_root=self.project_root,
                template_root=failing_template_root,
                profile_name="failing",
                namespace="super-dev",
            )

        self.assertEqual(agents_path.read_text(encoding="utf-8"), original_agents)
        state_path = self.project_root / ".codex" / "portable" / "state.json"
        self.assertFalse(state_path.exists())


if __name__ == "__main__":
    unittest.main()
