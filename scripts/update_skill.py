#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional, TextIO


NAME_PATTERN = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
SEARCH_RESULT_PATTERN = re.compile(r"^([^\s]+@[^\s]+)\s+.+installs$", re.MULTILINE)
DEFAULT_TIMEOUT_SECONDS = 60
LOCK_FILE_VERSION = 1


@dataclass(frozen=True)
class LocalSkill:
    name: str
    path: str
    source_dir: Path
    directory_name: str


@dataclass(frozen=True)
class LockEntry:
    name: str
    path: str
    mode: str
    reason: Optional[str]
    target: Optional[str]
    source: Optional[str]
    skill: Optional[str]
    repo_url: Optional[str]
    tracking_ref: Optional[str]
    resolved_commit: Optional[str]
    resolved_tag: Optional[str]
    applied_commit: Optional[str]
    applied_tag: Optional[str]


@dataclass(frozen=True)
class RemoteVersion:
    target: str
    source: str
    skill: str
    repo_url: str
    tracking_ref: str
    resolved_commit: str
    resolved_tag: Optional[str]


Finder = Callable[[str], list[str]]
Resolver = Callable[[str], RemoteVersion]
Installer = Callable[[Path, str, str], tuple[bool, str]]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_skills_root() -> Path:
    return repo_root() / "skills"


def default_lock_path() -> Path:
    return repo_root() / "skills.lock"


def normalize_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def strip_ansi(text: str) -> str:
    cleaned = ANSI_PATTERN.sub("", text)
    return cleaned.replace("\r", "")


def read_skill_name(skill_file: Path) -> Optional[str]:
    text = skill_file.read_text(encoding="utf-8")
    match = NAME_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).strip()


def collect_local_skills(skills_root: Path) -> list[LocalSkill]:
    skills: list[LocalSkill] = []
    for skill_file in sorted(skills_root.rglob("SKILL.md")):
        source_dir = skill_file.parent
        skills.append(
            LocalSkill(
                name=read_skill_name(skill_file) or source_dir.name,
                path=source_dir.relative_to(skills_root).as_posix(),
                source_dir=source_dir,
                directory_name=source_dir.name,
            )
        )
    return skills


def load_lock_file(lock_path: Path) -> dict[str, LockEntry]:
    if not lock_path.exists():
        return {}
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    items = payload.get("skills", [])
    entries: dict[str, LockEntry] = {}
    for item in items:
        normalized = dict(item)
        normalized.setdefault("mode", "tracked")
        normalized.setdefault("reason", None)
        normalized.setdefault("target", None)
        normalized.setdefault("source", None)
        normalized.setdefault("skill", None)
        normalized.setdefault("repo_url", None)
        normalized.setdefault("tracking_ref", None)
        normalized.setdefault("resolved_commit", None)
        normalized.setdefault("resolved_tag", None)
        normalized.setdefault("applied_commit", None)
        normalized.setdefault("applied_tag", None)
        entry = LockEntry(**normalized)
        entries[entry.name] = entry
    return entries


def save_lock_file(lock_path: Path, entries: dict[str, LockEntry]) -> None:
    payload = {
        "version": LOCK_FILE_VERSION,
        "skills": [asdict(entries[name]) for name in sorted(entries)],
    }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_list_rows(local_skills: list[LocalSkill], entries: dict[str, LockEntry]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for skill in local_skills:
        entry = entries.get(skill.name)
        rows.append(
            {
                "name": skill.name,
                "path": skill.path,
                "status": entry.mode if entry else "unlocked",
                "target": entry.target if entry and entry.target else "",
                "resolved_tag": (entry.resolved_tag or "") if entry else "",
                "resolved_commit": entry.resolved_commit if entry and entry.resolved_commit else "",
                "applied_commit": entry.applied_commit if entry and entry.applied_commit else "",
            }
        )
    return rows


def parse_find_results(output: str, requested_name: str) -> list[str]:
    cleaned = strip_ansi(output)
    exact_matches: list[str] = []
    fuzzy_matches: list[str] = []
    seen: set[str] = set()
    for match in SEARCH_RESULT_PATTERN.findall(cleaned):
        if match in seen:
            continue
        seen.add(match)
        skill_name = match.rsplit("@", 1)[-1]
        if skill_name == requested_name:
            exact_matches.append(match)
        else:
            fuzzy_matches.append(match)
    return exact_matches + fuzzy_matches


def run_command(command: list[str], cwd: Optional[Path] = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = strip_ansi((normalize_output(exc.stdout) + "\n" + normalize_output(exc.stderr)).strip())
        message = output or f"Command timed out after {timeout_seconds}s: {' '.join(command)}"
        return False, message
    output = strip_ansi((completed.stdout + "\n" + completed.stderr).strip())
    if completed.returncode == 0:
        return True, output
    return False, output or f"Command exited with {completed.returncode}: {' '.join(command)}"


def parse_target(target: str) -> tuple[str, str]:
    if "@" not in target:
        raise ValueError(f"Invalid target without @skill suffix: {target}")
    source, skill = target.rsplit("@", 1)
    if not source or not skill:
        raise ValueError(f"Invalid target: {target}")
    return source, skill


def build_repo_url(source: str) -> str:
    if source.startswith(("https://", "http://", "git@", "ssh://")):
        return source
    if "/" not in source:
        raise ValueError(f"Unsupported source format: {source}")
    return f"https://github.com/{source}.git"


def parse_ls_remote_output(output: str) -> tuple[str, str, Optional[str]]:
    tracking_ref = "HEAD"
    head_commit: Optional[str] = None
    tag_matches: list[str] = []
    cleaned = strip_ansi(output)
    for line in cleaned.splitlines():
        if not line.strip():
            continue
        if line.startswith("ref:") and line.endswith("\tHEAD"):
            parts = line.split()
            if len(parts) >= 2:
                tracking_ref = parts[1]
            continue
        if "\t" not in line:
            continue
        sha, ref = line.split("\t", 1)
        if ref == "HEAD":
            head_commit = sha
            continue
        if ref.startswith("refs/tags/"):
            tag_name = ref[len("refs/tags/") :].removesuffix("^{}")
            tag_matches.append((sha, tag_name))
    if not head_commit:
        raise ValueError("Could not resolve remote HEAD commit.")
    matching_tags = sorted({tag for sha, tag in tag_matches if sha == head_commit})
    return tracking_ref, head_commit, matching_tags[0] if matching_tags else None


def resolve_remote_version_via_git(target: str) -> RemoteVersion:
    source, skill = parse_target(target)
    repo_url = build_repo_url(source)
    success, output = run_command(["git", "ls-remote", "--symref", repo_url, "HEAD", "refs/tags/*"])
    if not success:
        raise ValueError(output)
    tracking_ref, resolved_commit, resolved_tag = parse_ls_remote_output(output)
    return RemoteVersion(
        target=target,
        source=source,
        skill=skill,
        repo_url=repo_url,
        tracking_ref=tracking_ref,
        resolved_commit=resolved_commit,
        resolved_tag=resolved_tag,
    )


def ensure_temp_project(workspace_root: Path) -> None:
    (workspace_root / "package.json").write_text(
        json.dumps({"name": "super-dev-skill-update-temp", "private": True}, indent=2) + "\n",
        encoding="utf-8",
    )


def find_candidates_via_npx(name: str) -> list[str]:
    workspace_root = Path(tempfile.mkdtemp(prefix="super-dev-find-"))
    try:
        ensure_temp_project(workspace_root)
        success, output = run_command(["npx", "-y", "skills", "find", name], cwd=workspace_root)
        candidates = parse_find_results(output, name)
        if not success and not candidates:
            raise ValueError(output or f'No skills found for "{name}"')
        return candidates
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def install_target_with_npx(workspace_root: Path, target: str, skill_name: str) -> tuple[bool, str]:
    ensure_temp_project(workspace_root)
    return run_command(["npx", "-y", "skills", "add", target, "-y", "--copy"], cwd=workspace_root)


def find_local_skill(skills_root: Path, name: str) -> LocalSkill:
    for skill in collect_local_skills(skills_root):
        if skill.name == name or skill.directory_name == name:
            return skill
    raise ValueError(f"Skill not found in local skills/: {name}")


def choose_candidate(name: str, candidates: list[str], input_fn: Callable[[str], str], output: TextIO) -> str:
    if not candidates:
        raise ValueError(f'No skills found for "{name}"')
    output.write(f"Candidates for {name}:\n")
    for index, candidate in enumerate(candidates, start=1):
        output.write(f"[{index}] {candidate}\n")
    while True:
        choice = input_fn(f"Select candidate for {name} [1-{len(candidates)}]: ").strip()
        if choice.isdigit():
            selected = int(choice)
            if 1 <= selected <= len(candidates):
                return candidates[selected - 1]
        output.write("Invalid selection. Try again.\n")


def blacklist_skill(name: str, skills_root: Path, lock_path: Path, reason: Optional[str] = None) -> LockEntry:
    local_skill = find_local_skill(skills_root, name)
    entries = load_lock_file(lock_path)
    entry = LockEntry(
        name=local_skill.name,
        path=local_skill.path,
        mode="blacklisted",
        reason=reason,
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
    entries[entry.name] = entry
    save_lock_file(lock_path, entries)
    return entry


def lock_skill(
    name: str,
    skills_root: Path,
    lock_path: Path,
    find_candidates: Finder = find_candidates_via_npx,
    resolve_remote_version: Resolver = resolve_remote_version_via_git,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> LockEntry:
    local_skill = find_local_skill(skills_root, name)
    candidates = find_candidates(local_skill.name)
    selected = choose_candidate(local_skill.name, candidates, input_fn=input_fn, output=output)
    remote = resolve_remote_version(selected)
    entries = load_lock_file(lock_path)
    previous_entry = entries.get(local_skill.name)
    entry = LockEntry(
        name=local_skill.name,
        path=local_skill.path,
        mode="tracked",
        reason=None,
        target=remote.target,
        source=remote.source,
        skill=remote.skill,
        repo_url=remote.repo_url,
        tracking_ref=remote.tracking_ref,
        resolved_commit=remote.resolved_commit,
        resolved_tag=remote.resolved_tag,
        applied_commit=(previous_entry.applied_commit if previous_entry and previous_entry.mode == "tracked" and previous_entry.target == remote.target else None),
        applied_tag=(previous_entry.applied_tag if previous_entry and previous_entry.mode == "tracked" and previous_entry.target == remote.target else None),
    )
    entries[entry.name] = entry
    save_lock_file(lock_path, entries)
    return entry


def find_installed_skill_dir(agents_root: Path, skill_name: str, fallback_name: str) -> Optional[Path]:
    candidate_by_dir: Optional[Path] = None
    for skill_file in sorted(agents_root.rglob("SKILL.md")):
        skill_dir = skill_file.parent
        installed_name = read_skill_name(skill_file)
        if installed_name == skill_name:
            return skill_dir
        if skill_dir.name == fallback_name and candidate_by_dir is None:
            candidate_by_dir = skill_dir
    return candidate_by_dir


def replace_directory(source_dir: Path, destination_dir: Path) -> None:
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, destination_dir)


def update_locked_skill(
    name: str,
    skills_root: Path,
    lock_path: Path,
    resolve_remote_version: Resolver = resolve_remote_version_via_git,
    installer: Installer = install_target_with_npx,
    dry_run: bool = False,
) -> dict[str, object]:
    local_skill = find_local_skill(skills_root, name)
    entries = load_lock_file(lock_path)
    if local_skill.name not in entries:
        return {
            "name": local_skill.name,
            "path": local_skill.path,
            "status": "unlocked",
            "message": "Skill is not present in skills.lock.",
        }

    entry = entries[local_skill.name]
    if entry.mode == "blacklisted":
        return {
            "name": local_skill.name,
            "path": local_skill.path,
            "status": "blacklisted",
            "message": entry.reason or "Skill is blacklisted.",
        }

    if not entry.target:
        return {
            "name": local_skill.name,
            "path": local_skill.path,
            "status": "failed",
            "message": "Tracked entry is missing target.",
        }

    remote = resolve_remote_version(entry.target)
    if entry.applied_commit and remote.resolved_commit == entry.applied_commit:
        return {
            "name": local_skill.name,
            "path": local_skill.path,
            "status": "already_latest",
            "message": f"Already at {entry.applied_commit}.",
            "target": entry.target,
            "resolved_commit": remote.resolved_commit,
        }

    with tempfile.TemporaryDirectory(prefix="super-dev-skill-update-") as tmp:
        workspace_root = Path(tmp)
        success, message = installer(workspace_root, entry.target, local_skill.name)
        if not success:
            return {
                "name": local_skill.name,
                "path": local_skill.path,
                "status": "failed",
                "message": message,
                "target": entry.target,
            }
        installed_dir = find_installed_skill_dir(
            workspace_root / ".agents",
            skill_name=local_skill.name,
            fallback_name=local_skill.directory_name,
        )
        if installed_dir is None:
            return {
                "name": local_skill.name,
                "path": local_skill.path,
                "status": "failed",
                "message": "Installed skill directory was not found under .agents.",
                "target": entry.target,
            }
        result = {
            "name": local_skill.name,
            "path": local_skill.path,
            "status": "dry-run" if dry_run else "updated",
            "message": message,
            "target": entry.target,
            "previous_commit": entry.applied_commit,
            "resolved_commit": remote.resolved_commit,
            "resolved_tag": remote.resolved_tag,
        }
        if dry_run:
            return result
        replace_directory(installed_dir, local_skill.source_dir)
        entries[local_skill.name] = LockEntry(
            name=local_skill.name,
            path=local_skill.path,
            mode="tracked",
            reason=None,
            target=remote.target,
            source=remote.source,
            skill=remote.skill,
            repo_url=remote.repo_url,
            tracking_ref=remote.tracking_ref,
            resolved_commit=remote.resolved_commit,
            resolved_tag=remote.resolved_tag,
            applied_commit=remote.resolved_commit,
            applied_tag=remote.resolved_tag,
        )
        save_lock_file(lock_path, entries)
        return result


def update_all_skills(
    skills_root: Path,
    lock_path: Path,
    resolve_remote_version: Resolver = resolve_remote_version_via_git,
    installer: Installer = install_target_with_npx,
    dry_run: bool = False,
) -> list[dict[str, object]]:
    entries = load_lock_file(lock_path)
    results: list[dict[str, object]] = []
    for skill in collect_local_skills(skills_root):
        if skill.name not in entries:
            results.append(
                {
                    "name": skill.name,
                    "path": skill.path,
                    "status": "unlocked",
                    "message": "Skill is not present in skills.lock.",
                }
            )
            continue
        results.append(
            update_locked_skill(
                name=skill.name,
                skills_root=skills_root,
                lock_path=lock_path,
                resolve_remote_version=resolve_remote_version,
                installer=installer,
                dry_run=dry_run,
            )
        )
    return results


def render_list(rows: list[dict[str, str]]) -> str:
    headers = ["name", "path", "status", "target", "resolved_tag", "resolved_commit", "applied_commit"]
    widths = {header: len(header) for header in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(row[header]))
    lines = ["  ".join(header.ljust(widths[header]) for header in headers)]
    for row in rows:
        lines.append("  ".join(row[header].ljust(widths[header]) for header in headers))
    return "\n".join(lines)


def summarize_results(results: list[dict[str, object]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for result in results:
        status = str(result["status"])
        summary[status] = summary.get(status, 0) + 1
    return summary


def parse_args_from(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lock-driven skill updater for this repository.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List local skills and lock status.")
    group.add_argument("--lock", metavar="NAME", help="Interactively lock a single skill into skills.lock.")
    group.add_argument("--blacklist", metavar="NAME", help="Mark a single skill as blacklisted in skills.lock.")
    group.add_argument("--name", metavar="NAME", help="Update a single locked skill.")
    group.add_argument("--all", action="store_true", help="Update all locked skills.")
    parser.add_argument("--skills-root", default=str(default_skills_root()), help="Path to local skills root.")
    parser.add_argument("--lock-file", default=str(default_lock_path()), help="Path to skills.lock JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve and install without replacing local skill directories.")
    return parser.parse_args(argv)


def parse_args() -> argparse.Namespace:
    return parse_args_from(sys.argv[1:])


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args() if argv is None else parse_args_from(argv)
    skills_root = Path(args.skills_root).resolve()
    lock_path = Path(args.lock_file).resolve()

    if args.list:
        rows = build_list_rows(collect_local_skills(skills_root), load_lock_file(lock_path))
        print(render_list(rows))
        return 0

    if args.blacklist:
        entry = blacklist_skill(name=args.blacklist, skills_root=skills_root, lock_path=lock_path)
        print(json.dumps(asdict(entry), ensure_ascii=False, indent=2))
        return 0

    if args.lock:
        entry = lock_skill(name=args.lock, skills_root=skills_root, lock_path=lock_path)
        print(json.dumps(asdict(entry), ensure_ascii=False, indent=2))
        return 0

    if args.name:
        result = update_locked_skill(
            name=args.name,
            skills_root=skills_root,
            lock_path=lock_path,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    results = update_all_skills(
        skills_root=skills_root,
        lock_path=lock_path,
        dry_run=args.dry_run,
    )
    print(json.dumps({"summary": summarize_results(results), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
