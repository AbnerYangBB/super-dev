import importlib.util
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "common" / "install" / "scripts" / "portable_dispatch.py"
SPEC = importlib.util.spec_from_file_location("portable_dispatch_impl", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module: {SCRIPT_PATH}")
DISPATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISPATCHER)


def _load_example_intent():
    path = REPO_ROOT / "common" / "platforms" / "intents" / "examples" / "pre-commit-sync-loc.json"
    return DISPATCHER.load_json(path)


class TestPortableDispatch(unittest.TestCase):
    def test_dispatch_hook_intent_outputs_platform_specific_actions(self):
        intent = _load_example_intent()
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)

        result = DISPATCHER.dispatch_intent(intent, matrix)

        self.assertIn("claude-code", result)
        self.assertIn("codex-cli", result)
        self.assertIn("trae-ide", result)
        self.assertIn("cursor-ide", result)
        self.assertEqual(result["claude-code"][0]["operation"], "merge_json_keys")
        self.assertEqual(result["codex-cli"][0]["operation"], "append_block")
        self.assertEqual(result["trae-ide"][0]["operation"], "append_block")
        self.assertEqual(result["cursor-ide"][0]["operation"], "append_block")
        self.assertEqual(result["trae-ide"][0]["target"], ".trae/rules/super-dev-rules.md")
        self.assertEqual(result["cursor-ide"][0]["target"], ".cursor/rules/agents.md")

    def test_dispatch_instruction_intent_generates_memory_actions(self):
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        intent = {
            "id": "shared_instruction",
            "feature_type": "instruction",
            "trigger": "always",
            "tool_ref": "instruction:keep-chinese",
            "desired_behavior": "all output in chinese",
            "platform_targets": ["claude-code", "codex-cli", "trae-ide", "cursor-ide"],
        }

        result = DISPATCHER.dispatch_intent(intent, matrix)
        self.assertEqual(result["claude-code"][0]["target"], "CLAUDE.md")
        self.assertEqual(result["codex-cli"][0]["target"], "AGENTS.md")
        self.assertEqual(result["trae-ide"][0]["target"], ".trae/rules/super-dev-rules.md")
        self.assertEqual(result["cursor-ide"][0]["target"], ".cursor/rules/agents.md")

    def test_dispatch_mcp_uses_intent_metadata_payload(self):
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        intent = {
            "id": "add_lint_mcp",
            "feature_type": "mcp",
            "trigger": "always",
            "tool_ref": "mcp:lint-server",
            "desired_behavior": "add lint mcp server",
            "platform_targets": ["claude-code", "codex-cli", "trae-ide", "cursor-ide"],
            "metadata": {
                "mcp_server": {
                    "name": "lint-server",
                    "command": "uvx",
                    "args": ["lint-mcp", "--stdio"],
                }
            },
        }

        result = DISPATCHER.dispatch_intent(intent, matrix)

        claude_server = result["claude-code"][0]["payload"]["mcpServers"]["lint-server"]
        codex_server = result["codex-cli"][0]["payload"]["mcp_servers"]["lint-server"]
        self.assertEqual(claude_server["command"], "uvx")
        self.assertEqual(codex_server["command"], "uvx")
        self.assertEqual(claude_server["args"], ["lint-mcp", "--stdio"])
        self.assertEqual(codex_server["args"], ["lint-mcp", "--stdio"])
        self.assertEqual(result["trae-ide"][0]["operation"], "merge_json_keys")
        self.assertEqual(result["trae-ide"][0]["target"], "mcp.json")
        trae_server = result["trae-ide"][0]["payload"]["mcpServers"]["lint-server"]
        self.assertEqual(trae_server["command"], "uvx")
        self.assertEqual(trae_server["args"], ["lint-mcp", "--stdio"])

        self.assertEqual(result["cursor-ide"][0]["operation"], "merge_json_keys")
        self.assertEqual(result["cursor-ide"][0]["target"], ".cursor/mcp.json")
        cursor_server = result["cursor-ide"][0]["payload"]["mcpServers"]["lint-server"]
        self.assertEqual(cursor_server["command"], "uvx")
        self.assertEqual(cursor_server["args"], ["lint-mcp", "--stdio"])

    def test_dispatch_hook_uses_metadata_command_for_claude(self):
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        intent = {
            "id": "pre_commit_custom_hook",
            "feature_type": "hook",
            "trigger": "pre_commit",
            "tool_ref": "hook:custom",
            "desired_behavior": "run linters before commit",
            "platform_targets": ["claude-code", "codex-cli", "trae-ide"],
            "metadata": {
                "hook_command": "python3 -m pytest -q",
            },
        }

        result = DISPATCHER.dispatch_intent(intent, matrix)
        hook_cmd = result["claude-code"][0]["payload"]["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertEqual(hook_cmd, "python3 -m pytest -q")
        self.assertEqual(result["codex-cli"][0]["operation"], "append_block")
        self.assertEqual(result["trae-ide"][0]["operation"], "append_block")

    def test_dispatch_only_targets_requested_platform(self):
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        intent = {
            "id": "codex_only_instruction",
            "feature_type": "instruction",
            "trigger": "always",
            "tool_ref": "instruction:codex-only",
            "desired_behavior": "only codex should get this",
            "platform_targets": ["codex-cli"],
        }
        result = DISPATCHER.dispatch_intent(intent, matrix)
        self.assertEqual(set(result.keys()), {"codex-cli"})

    def test_dispatch_skill_sync_targets_trae_skills_dir(self):
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        intent = {
            "id": "trae_skill_sync",
            "feature_type": "skill",
            "trigger": "always",
            "tool_ref": "skill:sync-add-ios-loc",
            "desired_behavior": "sync one skill into trae project skills",
            "platform_targets": ["trae-ide"],
        }
        result = DISPATCHER.dispatch_intent(intent, matrix)
        self.assertEqual(result["trae-ide"][0]["operation"], "sync_additive_dir")
        self.assertEqual(result["trae-ide"][0]["target"], ".trae/skills")


if __name__ == "__main__":
    unittest.main()
