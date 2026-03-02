#!/usr/bin/env python3
"""Run black-box verification cases for platform-feature-dispatcher skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any


def load_cases(path: pathlib.Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Cases file must be a JSON array")
    return data


def _flatten_actions(actions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for platform, items in actions.items():
        for item in items:
            out.append(
                {
                    "platform": platform,
                    "operation": item.get("operation"),
                    "target": item.get("target"),
                }
            )
    return out


def _snapshot_files(repo_path: pathlib.Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_path)
        if ".git" in rel.parts:
            continue
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
        snapshot[str(rel)] = digest
    return snapshot


def _diff_snapshot(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed: list[str] = []
    all_keys = set(before) | set(after)
    for key in sorted(all_keys):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def _collect_evidence(repo_path: pathlib.Path, files: list[str], patterns: list[str]) -> list[str]:
    evidence: list[str] = []
    for rel in files:
        path = repo_path / rel
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            for line in text.splitlines():
                if pattern in line:
                    evidence.append(f"{rel}: {line.strip()}")
    return evidence


def _copy_repo(repo_root: pathlib.Path, work_root: pathlib.Path, case_id: str) -> pathlib.Path:
    case_root = work_root / case_id
    repo_copy = case_root / "repo"
    case_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root, repo_copy)
    return repo_copy


def run_blackbox_case(
    *,
    repo_root: pathlib.Path,
    case: dict[str, Any],
    work_root: pathlib.Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    case_id = case["id"]
    repo_copy = _copy_repo(repo_root, work_root, case_id)
    skill_entry = (
        repo_copy
        / ".agents"
        / "skills"
        / "platform-feature-dispatcher"
        / "scripts"
        / "dispatch_from_prompt.py"
    )
    before_snapshot = _snapshot_files(repo_copy)

    cmd = [
        "python3",
        str(skill_entry),
        "--repo-root",
        str(repo_copy),
        "--prompt",
        case["prompt"],
        "--pretty",
    ]
    if dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        return {
            "id": case_id,
            "status": "failed",
            "error": proc.stderr.strip() or proc.stdout.strip(),
            "changed_files": [],
            "actual_actions": [],
            "evidence": [],
        }

    payload = json.loads(proc.stdout)
    actual_actions = _flatten_actions(payload.get("actions", {}))
    after_snapshot = _snapshot_files(repo_copy)
    changed_files = _diff_snapshot(before_snapshot, after_snapshot)

    expected_actions = case.get("expected_actions", [])
    expected_files = case.get("expected_changed_files", [])
    evidence_patterns = case.get("evidence_patterns", [])

    action_ok = all(expected in actual_actions for expected in expected_actions)
    files_ok = all(path in changed_files for path in expected_files)
    evidence = _collect_evidence(repo_copy, changed_files, evidence_patterns)
    evidence_ok = all(any(pattern in line for line in evidence) for pattern in evidence_patterns)

    status = "passed" if (action_ok and files_ok and evidence_ok) else "failed"

    return {
        "id": case_id,
        "status": status,
        "changed_files": changed_files,
        "expected_actions": expected_actions,
        "actual_actions": actual_actions,
        "evidence": evidence,
        "checks": {
            "action_ok": action_ok,
            "files_ok": files_ok,
            "evidence_ok": evidence_ok,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run skill black-box cases")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--cases", required=True, help="Path to cases JSON")
    parser.add_argument(
        "--output",
        default="tests/verification/blackbox-report.json",
        help="Output report path (relative to repo root if not absolute)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run dispatcher with --dry-run")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = pathlib.Path(args.repo_root).resolve()
    cases = load_cases(pathlib.Path(args.cases).resolve())

    with tempfile.TemporaryDirectory() as tmp:
        work_root = pathlib.Path(tmp)
        results = [
            run_blackbox_case(
                repo_root=repo_root,
                case=case,
                work_root=work_root,
                dry_run=args.dry_run,
            )
            for case in cases
        ]

    passed = sum(1 for item in results if item["status"] == "passed")
    failed = len(results) - passed

    report = {
        "status": "ok" if failed == 0 else "failed",
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
        },
        "results": results,
    }

    output_path = pathlib.Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
