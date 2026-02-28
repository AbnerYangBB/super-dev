import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestInstallDocs(unittest.TestCase):
    def test_install_doc_contains_hard_rules_and_apply_command(self):
        text = (REPO_ROOT / "common" / "install" / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("Hard Rules", text)
        self.assertIn("portable_apply.py", text)
        self.assertIn("仅允许修改 AI 配置文件", text)

    def test_rollback_doc_contains_latest_flow(self):
        text = (REPO_ROOT / "common" / "install" / "ROLLBACK.md").read_text(encoding="utf-8")
        self.assertIn("latest", text)
        self.assertIn("portable_rollback.py", text)


if __name__ == "__main__":
    unittest.main()
