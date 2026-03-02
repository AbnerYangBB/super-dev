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
        self.assertEqual(result["claude-code"][0]["operation"], "merge_json_keys")
        self.assertEqual(result["codex-cli"][0]["operation"], "append_block")

    def test_dispatch_instruction_intent_generates_memory_actions(self):
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        intent = {
            "id": "shared_instruction",
            "feature_type": "instruction",
            "trigger": "always",
            "tool_ref": "instruction:keep-chinese",
            "desired_behavior": "all output in chinese",
            "platform_targets": ["claude-code", "codex-cli"],
        }

        result = DISPATCHER.dispatch_intent(intent, matrix)
        self.assertEqual(result["claude-code"][0]["target"], "CLAUDE.md")
        self.assertEqual(result["codex-cli"][0]["target"], "AGENTS.md")


if __name__ == "__main__":
    unittest.main()
