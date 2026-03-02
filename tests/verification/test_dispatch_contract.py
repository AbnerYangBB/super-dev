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


class TestDispatchContract(unittest.TestCase):
    def test_dispatch_contract_pre_commit_hook(self):
        fixture = REPO_ROOT / "tests" / "verification" / "fixtures" / "intents" / "pre-commit-sync-loc.json"
        self.assertTrue(fixture.exists(), msg=f"Missing fixture: {fixture}")

        intent = DISPATCHER.load_json(fixture)
        matrix = DISPATCHER.load_capability_matrix(REPO_ROOT)
        result = DISPATCHER.dispatch_intent(intent, matrix)

        self.assertEqual(result["codex-cli"][0]["operation"], "append_block")
        self.assertIn(result["claude-code"][0]["operation"], {"merge_json_keys", "append_block"})


if __name__ == "__main__":
    unittest.main()
