#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

IGNORED_FILE_NAMES = {".DS_Store"}
IGNORED_DIR_NAMES = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync repository skills to a workspace .agents/skills/super-dev directory."
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Target workspace root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing files.",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def source_root() -> Path:
    return repo_root() / "skills"


def target_root(workspace_root: Path) -> Path:
    return workspace_root / ".agents" / "skills" / "super-dev"


def iter_source_files(root: Path) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not supported in source tree: {path}")
        if any(part in IGNORED_DIR_NAMES for part in path.parts):
            continue
        if path.name in IGNORED_FILE_NAMES:
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        if path.is_file():
            files[path.relative_to(root)] = path
    return files


def iter_target_files(root: Path) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    if not root.exists():
        return files
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or path.is_file():
            files[path.relative_to(root)] = path
    return files


def ensure_safe_parent(root: Path, destination: Path) -> None:
    current = root
    for part in destination.relative_to(root).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing to write through symlinked directory: {current}")


def same_contents(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    if left.stat().st_size != right.stat().st_size:
        return False
    return left.read_bytes() == right.read_bytes()


def remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def main() -> int:
    args = parse_args()

    workspace = Path(args.workspace_root).resolve()
    source = source_root()
    target = target_root(workspace)

    if not source.is_dir():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"Source skills directory does not exist: {source}",
                },
                ensure_ascii=True,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    source_files = iter_source_files(source)
    target_files = iter_target_files(target)

    copied: list[str] = []
    deleted: list[str] = []

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for relative_path, source_file in source_files.items():
        destination = target / relative_path
        if destination.is_symlink():
            raise ValueError(f"Refusing to overwrite symlinked file path: {destination}")

        if same_contents(source_file, destination):
            continue

        copied.append(relative_path.as_posix())

        if args.dry_run:
            continue

        ensure_safe_parent(target, destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)

    stale_paths = sorted(set(target_files) - set(source_files))
    for relative_path in stale_paths:
        stale_path = target / relative_path
        deleted.append(relative_path.as_posix())
        if args.dry_run:
            continue
        if stale_path.is_symlink():
            stale_path.unlink(missing_ok=True)
        elif stale_path.is_dir():
            shutil.rmtree(stale_path)
        else:
            stale_path.unlink(missing_ok=True)

    if not args.dry_run:
        remove_empty_dirs(target)

    summary = {
        "status": "ok",
        "workspace_root": str(workspace),
        "source_root": str(source),
        "target_root": str(target),
        "copied": copied,
        "deleted": deleted,
        "dry_run": args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(error),
                },
                ensure_ascii=True,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
