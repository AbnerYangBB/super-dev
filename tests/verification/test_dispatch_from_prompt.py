import importlib.util
import json
import pathlib
import subprocess
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "platform-feature-dispatcher" / "scripts" / "dispatch_from_prompt.py"
SPEC = importlib.util.spec_from_file_location("dispatch_from_prompt_impl", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module: {SCRIPT_PATH}")
DISPATCH_FROM_PROMPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISPATCH_FROM_PROMPT)


class TestDispatchFromPrompt(unittest.TestCase):
    def test_build_intent_defaults_to_all_supported_platforms(self):
        intent = DISPATCH_FROM_PROMPT._build_intent_from_prompt(
            "增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验"
        )
        self.assertEqual(intent["feature_type"], "hook")
        self.assertEqual(intent["platform_targets"], ["claude-code", "codex-cli", "trae-ide"])

    def test_build_intent_with_custom_mcp_command_and_platform(self):
        intent = DISPATCH_FROM_PROMPT._build_intent_from_prompt(
            "增加一个 MCP server: lint-server command: uvx args: lint-mcp --stdio 仅 codex"
        )
        self.assertEqual(intent["feature_type"], "mcp")
        self.assertEqual(intent["platform_targets"], ["codex-cli"])
        mcp_server = intent["metadata"]["mcp_server"]
        self.assertEqual(mcp_server["name"], "lint-server")
        self.assertEqual(mcp_server["command"], "uvx")
        self.assertEqual(mcp_server["args"], ["lint-mcp", "--stdio"])

    def test_build_intent_with_custom_hook_command_and_platform(self):
        intent = DISPATCH_FROM_PROMPT._build_intent_from_prompt(
            "增加一个 hook: 提交前执行 command: npm run lint 仅 claude"
        )
        self.assertEqual(intent["feature_type"], "hook")
        self.assertEqual(intent["platform_targets"], ["claude-code"])
        self.assertEqual(intent["metadata"]["hook_command"], "npm run lint")
        self.assertEqual(intent["trigger"], "pre_commit")

    def test_build_intent_with_trae_only_target(self):
        intent = DISPATCH_FROM_PROMPT._build_intent_from_prompt(
            "增加一个 instruction: 使用团队规则 仅 trae"
        )
        self.assertEqual(intent["feature_type"], "instruction")
        self.assertEqual(intent["platform_targets"], ["trae-ide"])

    def test_prompt_remove_semantics_returns_error(self):
        cmd = [
            "python3",
            str(SCRIPT_PATH),
            "--repo-root",
            str(REPO_ROOT),
            "--prompt",
            "删除一个 hook: pre-commit loc check",
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        output = proc.stderr.strip() or proc.stdout.strip()
        payload = json.loads(output)
        self.assertEqual(payload["status"], "error")
        self.assertIn("删除", payload["message"])


if __name__ == "__main__":
    unittest.main()
