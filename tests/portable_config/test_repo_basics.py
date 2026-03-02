import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestRepoBasics(unittest.TestCase):
    def test_readme_is_newbie_oriented_and_prompt_first(self):
        readme = REPO_ROOT / "README.md"
        self.assertTrue(readme.exists())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("super-dev", text)
        self.assertIn("目前仅用于自用", text)
        self.assertIn("可能存在风险", text)
        self.assertIn("仅支持 iOS 工程的 Codex / Claude / Trae 配置", text)

        section_scope = text.index("## 当前支持范围")
        section_quickstart = text.index("## 开箱即用")
        section_uninstall = text.index("## 卸载")
        section_customize = text.index("## 功能定制")
        section_faq = text.index("## 常见问题")
        self.assertLess(section_scope, section_quickstart)
        self.assertLess(section_quickstart, section_uninstall)
        self.assertLess(section_uninstall, section_customize)
        self.assertLess(section_customize, section_faq)

        self.assertIn("Fetch and follow instructions", text)
        self.assertIn("install profile codex-ios", text)
        self.assertIn("install profile claude-ios", text)
        self.assertIn("install profile trae-ios", text)
        self.assertIn("rollback latest transaction", text)
        self.assertIn("fork", text.lower())
        self.assertIn("platform-feature-dispatcher", text)

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
        self.assertIn(".codex/portable/template/", text)


if __name__ == "__main__":
    unittest.main()
