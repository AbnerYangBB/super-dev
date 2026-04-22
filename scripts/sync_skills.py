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
        description=(
            "Sync repository skills to workspace .agents/skills/super-dev and "
            "sync repository agent/ contents into workspace root (without the "
            "agent directory itself)."
        )
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


def source_skills_root() -> Path:
    return repo_root() / "skills"


def source_agent_root() -> Path:
    return repo_root() / "agent"


def target_skills_root(workspace_root: Path) -> Path:
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


def split_name_and_suffixes(name: str) -> tuple[str, str]:
    suffixes = "".join(Path(name).suffixes)
    if suffixes and name != suffixes:
        base = name[: -len(suffixes)]
    else:
        base = name
        suffixes = ""
    return base, suffixes


def backup_name(name: str, index: int = 0) -> str:
    base, suffixes = split_name_and_suffixes(name)
    marker = "-bak" if index == 0 else f"-bak-{index + 1}"
    return f"{base}{marker}{suffixes}"


def build_backup_path(path: Path) -> Path:
    index = 0
    while True:
        candidate = path.with_name(backup_name(path.name, index=index))
        if not candidate.exists():
            return candidate
        index += 1


def backup_path(path: Path, dry_run: bool) -> Path:
    if path.is_symlink():
        raise ValueError(f"Refusing to rename symlink path: {path}")
    destination = build_backup_path(path)
    if not dry_run:
        path.rename(destination)
    return destination


def record_backup(
    workspace_root: Path,
    source_path: Path,
    backup: Path,
    backed_up: list[dict[str, str]],
    seen: set[tuple[str, str]],
) -> None:
    original_relative = source_path.relative_to(workspace_root).as_posix()
    backup_relative = backup.relative_to(workspace_root).as_posix()
    key = (original_relative, backup_relative)
    if key in seen:
        return
    seen.add(key)
    backed_up.append({"path": original_relative, "backup": backup_relative})


def ensure_destination_parents(
    workspace_root: Path,
    destination: Path,
    dry_run: bool,
    backed_up: list[dict[str, str]],
    backed_up_seen: set[tuple[str, str]],
) -> None:
    current = workspace_root
    for part in destination.relative_to(workspace_root).parts[:-1]:
        current = current / part
        if current.exists() and not current.is_dir():
            backup = backup_path(current, dry_run=dry_run)
            record_backup(
                workspace_root=workspace_root,
                source_path=current,
                backup=backup,
                backed_up=backed_up,
                seen=backed_up_seen,
            )
        if not dry_run:
            current.mkdir(exist_ok=True)


def sync_skills(
    source: Path,
    target: Path,
    dry_run: bool,
) -> dict[str, object]:
    source_files = iter_source_files(source)
    target_files = iter_target_files(target)

    copied: list[str] = []
    deleted: list[str] = []

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for relative_path, source_file in source_files.items():
        destination = target / relative_path
        if destination.is_symlink():
            raise ValueError(f"Refusing to overwrite symlinked file path: {destination}")

        if same_contents(source_file, destination):
            continue

        copied.append(relative_path.as_posix())

        if dry_run:
            continue

        ensure_safe_parent(target, destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)

    stale_paths = sorted(set(target_files) - set(source_files))
    for relative_path in stale_paths:
        stale_path = target / relative_path
        deleted.append(relative_path.as_posix())
        if dry_run:
            continue
        if stale_path.is_symlink():
            stale_path.unlink(missing_ok=True)
        elif stale_path.is_dir():
            shutil.rmtree(stale_path)
        else:
            stale_path.unlink(missing_ok=True)

    if not dry_run:
        remove_empty_dirs(target)

    return {
        "source_root": str(source),
        "target_root": str(target),
        "copied": copied,
        "deleted": deleted,
    }


def sync_agent(
    source: Path,
    workspace_root: Path,
    dry_run: bool,
) -> dict[str, object]:
    source_files = iter_source_files(source)

    copied: list[str] = []
    backed_up: list[dict[str, str]] = []
    backed_up_seen: set[tuple[str, str]] = set()

    for relative_path, source_file in source_files.items():
        # Agent files are copied to workspace root using paths relative to
        # source agent root, so we never create workspace_root/agent/*.
        if relative_path.parts and relative_path.parts[0] == "agent":
            raise ValueError(
                f"Invalid source path for agent sync, got nested agent prefix: "
                f"{relative_path}"
            )
        destination = workspace_root / relative_path

        if destination.is_symlink():
            raise ValueError(f"Refusing to overwrite symlinked file path: {destination}")

        ensure_destination_parents(
            workspace_root,
            destination,
            dry_run=dry_run,
            backed_up=backed_up,
            backed_up_seen=backed_up_seen,
        )

        if destination.exists() and destination.is_dir():
            backup = backup_path(destination, dry_run=dry_run)
            record_backup(
                workspace_root=workspace_root,
                source_path=destination,
                backup=backup,
                backed_up=backed_up,
                seen=backed_up_seen,
            )

        if destination.exists() and same_contents(source_file, destination):
            continue

        if destination.exists():
            backup = backup_path(destination, dry_run=dry_run)
            record_backup(
                workspace_root=workspace_root,
                source_path=destination,
                backup=backup,
                backed_up=backed_up,
                seen=backed_up_seen,
            )

        copied.append(relative_path.as_posix())

        if dry_run:
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)

    return {
        "source_root": str(source),
        "target_root": str(workspace_root),
        "copied": copied,
        "backed_up": backed_up,
    }


def main() -> int:
    args = parse_args()

    workspace = Path(args.workspace_root).resolve()
    skills_source = source_skills_root()
    agent_source = source_agent_root()
    skills_target = target_skills_root(workspace)

    if not skills_source.is_dir():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"Source skills directory does not exist: {skills_source}",
                },
                ensure_ascii=True,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    if not agent_source.is_dir():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"Source agent directory does not exist: {agent_source}",
                },
                ensure_ascii=True,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    skills_summary = sync_skills(
        source=skills_source,
        target=skills_target,
        dry_run=args.dry_run,
    )

    agent_summary = sync_agent(
        source=agent_source,
        workspace_root=workspace,
        dry_run=args.dry_run,
    )

    summary = {
        "status": "ok",
        "workspace_root": str(workspace),
        "dry_run": args.dry_run,
        "skills_sync": skills_summary,
        "agent_sync": agent_summary,
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
