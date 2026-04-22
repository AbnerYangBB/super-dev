import io
import tempfile
import unittest
from pathlib import Path

from scripts.update_skill import (
    LockEntry,
    RemoteVersion,
    blacklist_skill,
    build_list_rows,
    collect_local_skills,
    load_lock_file,
    lock_skill,
    parse_find_results,
    save_lock_file,
    update_all_skills,
    update_locked_skill,
)


class UpdateSkillTests(unittest.TestCase):
    def test_collect_local_skills_and_build_list_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\n", encoding="utf-8")
            ux = skills_root / "design" / "ui-ux-pro-max"
            ux.mkdir(parents=True)
            (ux / "SKILL.md").write_text("# missing frontmatter name\n", encoding="utf-8")

            entries = {
                "frontend-design": LockEntry(
                    name="frontend-design",
                    path="web/frontend-design",
                    mode="tracked",
                    reason=None,
                    target="anthropics/skills@frontend-design",
                    source="anthropics/skills",
                    skill="frontend-design",
                    repo_url="https://github.com/anthropics/skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="abc123",
                    resolved_tag=None,
                    applied_commit="abc122",
                    applied_tag=None,
                )
            }

            rows = build_list_rows(collect_local_skills(skills_root), entries)

            self.assertEqual(rows[0]["name"], "ui-ux-pro-max")
            self.assertEqual(rows[0]["status"], "unlocked")
            self.assertEqual(rows[1]["name"], "frontend-design")
            self.assertEqual(rows[1]["status"], "tracked")
            self.assertEqual(rows[1]["target"], "anthropics/skills@frontend-design")
            self.assertEqual(rows[1]["resolved_commit"], "abc123")
            self.assertEqual(rows[1]["applied_commit"], "abc122")

    def test_parse_find_results_prefers_exact_matches(self) -> None:
        output = """\
Install with npx skills add <owner/repo@skill>

anthropics/skills@frontend-design 323.5K installs
smithery.ai@frontend-design 2.6K installs
supercent-io/skills-template@frontend-design-system 8.5K installs
"""
        self.assertEqual(
            parse_find_results(output, "frontend-design"),
            [
                "anthropics/skills@frontend-design",
                "smithery.ai@frontend-design",
                "supercent-io/skills-template@frontend-design-system",
            ],
        )

    def test_save_and_load_lock_file_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "skills.lock"
            entries = {
                "frontend-design": LockEntry(
                    name="frontend-design",
                    path="web/frontend-design",
                    mode="tracked",
                    reason=None,
                    target="anthropics/skills@frontend-design",
                    source="anthropics/skills",
                    skill="frontend-design",
                    repo_url="https://github.com/anthropics/skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="abc123",
                    resolved_tag="v1.0.0",
                    applied_commit="abc122",
                    applied_tag=None,
                )
            }

            save_lock_file(lock_path, entries)
            loaded = load_lock_file(lock_path)

            self.assertEqual(loaded["frontend-design"].resolved_commit, "abc123")
            self.assertEqual(loaded["frontend-design"].resolved_tag, "v1.0.0")
            self.assertEqual(loaded["frontend-design"].applied_commit, "abc122")
            self.assertEqual(loaded["frontend-design"].mode, "tracked")

    def test_blacklist_skill_reuses_lock_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            accessibility = skills_root / "web" / "web-accessibility"
            accessibility.mkdir(parents=True)
            (accessibility / "SKILL.md").write_text("---\nname: web-accessibility\n---\n", encoding="utf-8")
            lock_path = root / "skills.lock"

            entry = blacklist_skill("web-accessibility", skills_root=skills_root, lock_path=lock_path)

            self.assertEqual(entry.mode, "blacklisted")
            self.assertEqual(entry.name, "web-accessibility")
            loaded = load_lock_file(lock_path)
            self.assertEqual(loaded["web-accessibility"].mode, "blacklisted")
            self.assertIsNone(loaded["web-accessibility"].target)

    def test_lock_skill_converts_blacklisted_skill_back_to_tracked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            save_lock_file(
                lock_path,
                {
                    "frontend-design": LockEntry(
                        name="frontend-design",
                        path="web/frontend-design",
                        mode="blacklisted",
                        reason="manual",
                        target=None,
                        source=None,
                        skill=None,
                        repo_url=None,
                        tracking_ref=None,
                        resolved_commit=None,
                        resolved_tag=None,
                        applied_commit=None,
                        applied_tag=None,
                    )
                },
            )
            transcript = io.StringIO()

            def fake_find(name: str) -> list[str]:
                return ["anthropics/skills@frontend-design"]

            def fake_resolve(target: str) -> RemoteVersion:
                return RemoteVersion(
                    target=target,
                    source="anthropics/skills",
                    skill="frontend-design",
                    repo_url="https://github.com/anthropics/skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="abc123",
                    resolved_tag=None,
                )

            entry = lock_skill(
                name="frontend-design",
                skills_root=skills_root,
                lock_path=lock_path,
                find_candidates=fake_find,
                resolve_remote_version=fake_resolve,
                input_fn=lambda _: "1",
                output=transcript,
            )

            self.assertEqual(entry.mode, "tracked")
            loaded = load_lock_file(lock_path)
            self.assertEqual(loaded["frontend-design"].mode, "tracked")
            self.assertEqual(loaded["frontend-design"].target, "anthropics/skills@frontend-design")

    def test_lock_skill_records_selected_candidate_but_marks_local_as_unapplied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            transcript = io.StringIO()

            def fake_find(name: str) -> list[str]:
                self.assertEqual(name, "frontend-design")
                return [
                    "anthropics/skills@frontend-design",
                    "jwynia/agent-skills@frontend-design",
                ]

            def fake_resolve(target: str) -> RemoteVersion:
                self.assertEqual(target, "jwynia/agent-skills@frontend-design")
                return RemoteVersion(
                    target=target,
                    source="jwynia/agent-skills",
                    skill="frontend-design",
                    repo_url="https://github.com/jwynia/agent-skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="def456",
                    resolved_tag=None,
                )

            entry = lock_skill(
                name="frontend-design",
                skills_root=skills_root,
                lock_path=lock_path,
                find_candidates=fake_find,
                resolve_remote_version=fake_resolve,
                input_fn=lambda _: "2",
                output=transcript,
            )

            self.assertEqual(entry.target, "jwynia/agent-skills@frontend-design")
            self.assertEqual(entry.mode, "tracked")
            self.assertIsNone(entry.applied_commit)
            loaded = load_lock_file(lock_path)
            self.assertEqual(loaded["frontend-design"].resolved_commit, "def456")
            self.assertIsNone(loaded["frontend-design"].applied_commit)
            self.assertIn("[1] anthropics/skills@frontend-design", transcript.getvalue())
            self.assertIn("[2] jwynia/agent-skills@frontend-design", transcript.getvalue())

    def test_update_locked_skill_returns_blacklisted_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            accessibility = skills_root / "web" / "web-accessibility"
            accessibility.mkdir(parents=True)
            (accessibility / "SKILL.md").write_text("---\nname: web-accessibility\n---\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            save_lock_file(
                lock_path,
                {
                    "web-accessibility": LockEntry(
                        name="web-accessibility",
                        path="web/web-accessibility",
                        mode="blacklisted",
                        reason="manual",
                        target=None,
                        source=None,
                        skill=None,
                        repo_url=None,
                        tracking_ref=None,
                        resolved_commit=None,
                        resolved_tag=None,
                        applied_commit=None,
                        applied_tag=None,
                    )
                },
            )

            result = update_locked_skill(name="web-accessibility", skills_root=skills_root, lock_path=lock_path)

            self.assertEqual(result["status"], "blacklisted")

    def test_update_locked_skill_requires_apply_when_only_lock_was_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\nold\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            save_lock_file(
                lock_path,
                {
                    "frontend-design": LockEntry(
                        name="frontend-design",
                        path="web/frontend-design",
                        mode="tracked",
                        reason=None,
                        target="anthropics/skills@frontend-design",
                        source="anthropics/skills",
                        skill="frontend-design",
                        repo_url="https://github.com/anthropics/skills.git",
                        tracking_ref="refs/heads/main",
                        resolved_commit="abc123",
                        resolved_tag=None,
                        applied_commit=None,
                        applied_tag=None,
                    )
                },
            )

            def fake_resolve(target: str) -> RemoteVersion:
                self.assertEqual(target, "anthropics/skills@frontend-design")
                return RemoteVersion(
                    target=target,
                    source="anthropics/skills",
                    skill="frontend-design",
                    repo_url="https://github.com/anthropics/skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="abc123",
                    resolved_tag=None,
                )

            def fake_installer(workspace_root: Path, target: str, skill_name: str) -> tuple[bool, str]:
                installed_dir = workspace_root / ".agents" / "skills" / "frontend-design"
                installed_dir.mkdir(parents=True)
                (installed_dir / "SKILL.md").write_text("---\nname: frontend-design\n---\nnew\n", encoding="utf-8")
                return True, "installed"

            result = update_locked_skill(
                name="frontend-design",
                skills_root=skills_root,
                lock_path=lock_path,
                resolve_remote_version=fake_resolve,
                installer=fake_installer,
                dry_run=True,
            )

            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(result["resolved_commit"], "abc123")

    def test_update_locked_skill_skips_when_applied_commit_is_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\nold\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            save_lock_file(
                lock_path,
                {
                    "frontend-design": LockEntry(
                        name="frontend-design",
                        path="web/frontend-design",
                        mode="tracked",
                        reason=None,
                        target="anthropics/skills@frontend-design",
                        source="anthropics/skills",
                        skill="frontend-design",
                        repo_url="https://github.com/anthropics/skills.git",
                        tracking_ref="refs/heads/main",
                        resolved_commit="abc123",
                        resolved_tag=None,
                        applied_commit="abc123",
                        applied_tag=None,
                    )
                },
            )

            calls = {"installer": 0}

            def fake_resolve(target: str) -> RemoteVersion:
                self.assertEqual(target, "anthropics/skills@frontend-design")
                return RemoteVersion(
                    target=target,
                    source="anthropics/skills",
                    skill="frontend-design",
                    repo_url="https://github.com/anthropics/skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="abc123",
                    resolved_tag=None,
                )

            def fake_installer(workspace_root: Path, target: str, skill_name: str) -> tuple[bool, str]:
                calls["installer"] += 1
                return True, "installed"

            result = update_locked_skill(
                name="frontend-design",
                skills_root=skills_root,
                lock_path=lock_path,
                resolve_remote_version=fake_resolve,
                installer=fake_installer,
            )

            self.assertEqual(result["status"], "already_latest")
            self.assertEqual(calls["installer"], 0)

    def test_update_locked_skill_replaces_directory_and_updates_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\nold\n", encoding="utf-8")
            (frontend / "old.txt").write_text("stale\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            save_lock_file(
                lock_path,
                {
                    "frontend-design": LockEntry(
                        name="frontend-design",
                        path="web/frontend-design",
                        mode="tracked",
                        reason=None,
                        target="jwynia/agent-skills@frontend-design",
                        source="jwynia/agent-skills",
                        skill="frontend-design",
                        repo_url="https://github.com/jwynia/agent-skills.git",
                        tracking_ref="refs/heads/main",
                        resolved_commit="oldcommit",
                        resolved_tag=None,
                        applied_commit="oldcommit",
                        applied_tag=None,
                    )
                },
            )

            def fake_resolve(target: str) -> RemoteVersion:
                self.assertEqual(target, "jwynia/agent-skills@frontend-design")
                return RemoteVersion(
                    target=target,
                    source="jwynia/agent-skills",
                    skill="frontend-design",
                    repo_url="https://github.com/jwynia/agent-skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="newcommit",
                    resolved_tag="v2.0.0",
                )

            def fake_installer(workspace_root: Path, target: str, skill_name: str) -> tuple[bool, str]:
                self.assertEqual(skill_name, "frontend-design")
                installed_dir = workspace_root / ".agents" / "skills" / "frontend-design"
                installed_dir.mkdir(parents=True)
                (installed_dir / "SKILL.md").write_text(
                    "---\nname: frontend-design\n---\nnew\n",
                    encoding="utf-8",
                )
                (installed_dir / "new.txt").write_text("fresh\n", encoding="utf-8")
                return True, "installed"

            result = update_locked_skill(
                name="frontend-design",
                skills_root=skills_root,
                lock_path=lock_path,
                resolve_remote_version=fake_resolve,
                installer=fake_installer,
            )

            self.assertEqual(result["status"], "updated")
            self.assertFalse((frontend / "old.txt").exists())
            self.assertEqual((frontend / "new.txt").read_text(encoding="utf-8"), "fresh\n")
            loaded = load_lock_file(lock_path)
            self.assertEqual(loaded["frontend-design"].resolved_commit, "newcommit")
            self.assertEqual(loaded["frontend-design"].resolved_tag, "v2.0.0")
            self.assertEqual(loaded["frontend-design"].applied_commit, "newcommit")
            self.assertEqual(loaded["frontend-design"].applied_tag, "v2.0.0")

    def test_update_all_skills_reports_unlocked_and_blacklisted_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            frontend = skills_root / "web" / "frontend-design"
            frontend.mkdir(parents=True)
            (frontend / "SKILL.md").write_text("---\nname: frontend-design\n---\n", encoding="utf-8")
            ux = skills_root / "design" / "ui-ux-pro-max"
            ux.mkdir(parents=True)
            (ux / "SKILL.md").write_text("# missing frontmatter\n", encoding="utf-8")
            accessibility = skills_root / "web" / "web-accessibility"
            accessibility.mkdir(parents=True)
            (accessibility / "SKILL.md").write_text("---\nname: web-accessibility\n---\n", encoding="utf-8")
            lock_path = root / "skills.lock"
            save_lock_file(
                lock_path,
                {
                    "frontend-design": LockEntry(
                        name="frontend-design",
                        path="web/frontend-design",
                        mode="tracked",
                        reason=None,
                        target="anthropics/skills@frontend-design",
                        source="anthropics/skills",
                        skill="frontend-design",
                        repo_url="https://github.com/anthropics/skills.git",
                        tracking_ref="refs/heads/main",
                        resolved_commit="abc123",
                        resolved_tag=None,
                        applied_commit="abc123",
                        applied_tag=None,
                    ),
                    "web-accessibility": LockEntry(
                        name="web-accessibility",
                        path="web/web-accessibility",
                        mode="blacklisted",
                        reason="manual",
                        target=None,
                        source=None,
                        skill=None,
                        repo_url=None,
                        tracking_ref=None,
                        resolved_commit=None,
                        resolved_tag=None,
                        applied_commit=None,
                        applied_tag=None,
                    ),
                },
            )

            def fake_resolve(target: str) -> RemoteVersion:
                return RemoteVersion(
                    target=target,
                    source="anthropics/skills",
                    skill="frontend-design",
                    repo_url="https://github.com/anthropics/skills.git",
                    tracking_ref="refs/heads/main",
                    resolved_commit="abc123",
                    resolved_tag=None,
                )

            def fake_installer(workspace_root: Path, target: str, skill_name: str) -> tuple[bool, str]:
                return True, "installed"

            results = update_all_skills(
                skills_root=skills_root,
                lock_path=lock_path,
                resolve_remote_version=fake_resolve,
                installer=fake_installer,
            )

            self.assertEqual(results[0]["status"], "unlocked")
            self.assertEqual(results[1]["status"], "already_latest")
            self.assertEqual(results[2]["status"], "blacklisted")


if __name__ == "__main__":
    unittest.main()
