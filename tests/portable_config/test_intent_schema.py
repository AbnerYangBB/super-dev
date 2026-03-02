import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT_DIR = REPO_ROOT / "common" / "platforms" / "intents"


class TestIntentSchema(unittest.TestCase):
    def test_intent_schema_exists(self):
        schema = INTENT_DIR / "schema.json"
        self.assertTrue(schema.exists(), msg=f"Missing intent schema: {schema}")

    def test_pre_commit_intent_example_is_valid(self):
        intent_path = INTENT_DIR / "examples" / "pre-commit-sync-loc.json"
        self.assertTrue(intent_path.exists(), msg=f"Missing intent example: {intent_path}")
        intent = json.loads(intent_path.read_text(encoding="utf-8"))

        self.assertEqual(intent["feature_type"], "hook")
        self.assertEqual(intent["trigger"], "pre_commit")
        self.assertIn("sync-add-ios-loc", intent["tool_ref"])
        self.assertIn("claude-code", intent["platform_targets"])
        self.assertIn("codex-cli", intent["platform_targets"])
        self.assertIn("trae-ide", intent["platform_targets"])


if __name__ == "__main__":
    unittest.main()
