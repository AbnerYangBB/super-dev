import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestRepoBasics(unittest.TestCase):
    def test_readme_exists_with_scope_and_risk_notice(self):
        readme = REPO_ROOT / "README.md"
        self.assertTrue(readme.exists())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("super-dev", text)
        self.assertIn("目前仅用于自用", text)
        self.assertIn("可能存在风险", text)
        self.assertIn("仅支持 iOS 工程的 Codex 配置", text)
        self.assertIn("Fetch and follow instructions", text)

    def test_common_github_community_files_exist(self):
        self.assertTrue((REPO_ROOT / "CONTRIBUTING.md").exists())
        self.assertTrue((REPO_ROOT / "SECURITY.md").exists())
        self.assertTrue((REPO_ROOT / ".github" / "pull_request_template.md").exists())
        self.assertTrue((REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").exists())
        self.assertTrue((REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml").exists())

    def test_gitignore_covers_common_local_artifacts(self):
        gitignore = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore.exists())
        text = gitignore.read_text(encoding="utf-8")
        self.assertIn(".DS_Store", text)
        self.assertIn("__pycache__/", text)
        self.assertIn("*.pyc", text)


if __name__ == "__main__":
    unittest.main()
