import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CAP_DIR = REPO_ROOT / "common" / "platforms" / "capabilities"


class TestCapabilityMatrix(unittest.TestCase):
    def test_capability_matrix_has_required_fields(self):
        for filename in ("claude-code.json", "codex-cli.json", "trae-ide.json"):
            path = CAP_DIR / filename
            self.assertTrue(path.exists(), msg=f"Missing matrix file: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertIn("platform", payload)
            self.assertIn("verified_at", payload)
            self.assertIn("capabilities", payload)
            self.assertIsInstance(payload["capabilities"], list)
            self.assertGreater(len(payload["capabilities"]), 0)

            for item in payload["capabilities"]:
                self.assertIn("id", item)
                self.assertIn("support", item)
                self.assertIn("config_path", item)
                self.assertIn("fallback", item)
                self.assertIn("source_url", item)
                self.assertIn("purpose", item)
                self.assertIn(item["support"], {"supported", "unsupported", "fallback_required"})

    def test_schema_file_exists(self):
        schema = CAP_DIR / "schema.json"
        self.assertTrue(schema.exists(), msg=f"Missing schema file: {schema}")


if __name__ == "__main__":
    unittest.main()
