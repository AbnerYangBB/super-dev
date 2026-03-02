import importlib.util
import pathlib
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verification" / "run_skill_blackbox.py"
SPEC = importlib.util.spec_from_file_location("skill_blackbox_impl", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module: {SCRIPT_PATH}")
BLACKBOX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BLACKBOX)


class TestSkillBlackbox(unittest.TestCase):
    def test_skill_blackbox_case_pre_commit_loc(self):
        cases_path = REPO_ROOT / "tests" / "verification" / "skill_blackbox_cases.json"
        self.assertTrue(cases_path.exists(), msg=f"Missing blackbox cases: {cases_path}")
        cases = BLACKBOX.load_cases(cases_path)

        case = next(item for item in cases if item["id"] == "pre_commit_loc")
        with tempfile.TemporaryDirectory() as tmp:
            report = BLACKBOX.run_blackbox_case(
                repo_root=REPO_ROOT,
                case=case,
                work_root=pathlib.Path(tmp),
            )

        self.assertEqual(report["status"], "passed")
        self.assertIn("ios/codex/AGENTS.md", report["changed_files"])
        self.assertTrue(any("sync-add-ios-loc" in line for line in report["evidence"]))


if __name__ == "__main__":
    unittest.main()
