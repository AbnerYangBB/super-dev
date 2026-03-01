#!/usr/bin/env python3
"""Portable AI config installer core logic."""

from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import shutil
import tomllib
from typing import Any


class PortableConfigError(RuntimeError):
    """Raised when installer state or metadata is invalid."""


def load_profile_and_manifest(template_root: pathlib.Path, profile_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    profile_path = template_root / "common" / "install" / "profiles" / f"{profile_name}.json"
    manifest_path = template_root / "common" / "install" / "manifests" / f"{profile_name}.json"

    if not profile_path.exists():
        raise PortableConfigError(f"Profile not found: {profile_path}")
    if not manifest_path.exists():
        raise PortableConfigError(f"Manifest not found: {manifest_path}")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if profile.get("profile") != profile_name:
        raise PortableConfigError("Profile name mismatch")
    if manifest.get("profile") != profile_name:
        raise PortableConfigError("Manifest profile mismatch")
    if not isinstance(manifest.get("actions"), list) or not manifest["actions"]:
        raise PortableConfigError("Manifest actions must be non-empty list")

    return profile, manifest


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_txn_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _format_target(template: str, namespace: str) -> str:
    return template.format(skill_namespace=namespace)


def _load_state(state_path: pathlib.Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"transactions": []}
    return json.loads(state_path.read_text(encoding="utf-8"))


def _save_state(state_path: pathlib.Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_parent(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _backup_file(
    *,
    project_root: pathlib.Path,
    file_path: pathlib.Path,
    backup_root: pathlib.Path,
) -> str:
    rel = file_path.relative_to(project_root)
    backup_path = backup_root / "files" / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    return str(backup_path.relative_to(project_root))


def _hash_bytes(path: pathlib.Path) -> bytes:
    return path.read_bytes()


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> bool:
    changed = False
    for key, value in source.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
            changed = True
            continue
        target_value = target[key]
        if isinstance(target_value, dict) and isinstance(value, dict):
            if _merge_missing(target_value, value):
                changed = True
    return changed


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(item) for item in value) + "]"
    raise PortableConfigError(f"Unsupported TOML value type: {type(value)!r}")


def _toml_dump(data: dict[str, Any]) -> str:
    lines: list[str] = []

    def emit_table(table: dict[str, Any], prefix: str | None) -> None:
        if prefix:
            lines.append(f"[{prefix}]")

        scalars: list[tuple[str, Any]] = []
        subtables: list[tuple[str, dict[str, Any]]] = []
        for key, value in table.items():
            if isinstance(value, dict):
                subtables.append((key, value))
            else:
                scalars.append((key, value))

        for key, value in scalars:
            lines.append(f"{key} = {_format_toml_value(value)}")

        if scalars and subtables:
            lines.append("")

        for idx, (subkey, subtable) in enumerate(subtables):
            new_prefix = subkey if prefix is None else f"{prefix}.{subkey}"
            emit_table(subtable, new_prefix)
            if idx != len(subtables) - 1:
                lines.append("")

    emit_table(data, None)
    return "\n".join(lines).strip() + "\n"


def _append_block(
    *,
    action_id: str,
    src: pathlib.Path,
    dst: pathlib.Path,
    namespace: str,
    project_root: pathlib.Path,
    backup_root: pathlib.Path,
    txn_changes: list[dict[str, Any]],
) -> None:
    marker = namespace.upper()
    begin = f"# BEGIN {marker} MANAGED BLOCK:{action_id}"
    end = f"# END {marker} MANAGED BLOCK:{action_id}"
    source_body = src.read_text(encoding="utf-8").rstrip("\n")
    managed_block = f"{begin}\n{source_body}\n{end}\n"

    rel_path = str(dst.relative_to(project_root))

    if dst.exists():
        old = dst.read_text(encoding="utf-8")
        if begin in old and end in old:
            start = old.index(begin)
            stop = old.index(end, start) + len(end)
            prefix = old[:start]
            suffix = old[stop:]
            if suffix.startswith("\n"):
                suffix = suffix[1:]
            new = prefix.rstrip("\n") + "\n\n" + managed_block + suffix
        else:
            new = old.rstrip("\n") + "\n\n" + managed_block

        if new != old:
            backup_rel = _backup_file(project_root=project_root, file_path=dst, backup_root=backup_root)
            _ensure_parent(dst)
            dst.write_text(new, encoding="utf-8")
            txn_changes.append(
                {
                    "path": rel_path,
                    "operation": "updated",
                    "backup": backup_rel,
                    "action_id": action_id,
                }
            )
        return

    _ensure_parent(dst)
    dst.write_text(managed_block, encoding="utf-8")
    txn_changes.append(
        {
            "path": rel_path,
            "operation": "created",
            "backup": None,
            "action_id": action_id,
        }
    )


def _merge_toml_keys(
    *,
    action_id: str,
    src: pathlib.Path,
    dst: pathlib.Path,
    project_root: pathlib.Path,
    backup_root: pathlib.Path,
    conflict_root: pathlib.Path,
    txn_changes: list[dict[str, Any]],
    txn_conflicts: list[dict[str, Any]],
) -> None:
    src_text = src.read_text(encoding="utf-8")
    src_data = tomllib.loads(src_text)
    rel_path = str(dst.relative_to(project_root))

    if not dst.exists():
        _ensure_parent(dst)
        dst.write_text(src_text if src_text.endswith("\n") else src_text + "\n", encoding="utf-8")
        txn_changes.append(
            {
                "path": rel_path,
                "operation": "created",
                "backup": None,
                "action_id": action_id,
            }
        )
        return

    target_text = dst.read_text(encoding="utf-8")
    try:
        target_data = tomllib.loads(target_text)
    except tomllib.TOMLDecodeError:
        conflict_file = conflict_root / rel_path.replace("/", "__")
        conflict_file.parent.mkdir(parents=True, exist_ok=True)
        conflict_file.write_text(src_text, encoding="utf-8")
        txn_conflicts.append(
            {
                "path": rel_path,
                "reason": "target_toml_invalid",
                "suggested_source": str(conflict_file.relative_to(project_root)),
            }
        )
        return

    merged = copy.deepcopy(target_data)
    changed = _merge_missing(merged, src_data)
    if not changed:
        return

    backup_rel = _backup_file(project_root=project_root, file_path=dst, backup_root=backup_root)
    dumped = _toml_dump(merged)
    dst.write_text(dumped, encoding="utf-8")
    txn_changes.append(
        {
            "path": rel_path,
            "operation": "updated",
            "backup": backup_rel,
            "action_id": action_id,
        }
    )


def _merge_json_keys(
    *,
    action_id: str,
    src: pathlib.Path,
    dst: pathlib.Path,
    project_root: pathlib.Path,
    backup_root: pathlib.Path,
    conflict_root: pathlib.Path,
    txn_changes: list[dict[str, Any]],
    txn_conflicts: list[dict[str, Any]],
) -> None:
    src_text = src.read_text(encoding="utf-8")
    try:
        src_data = json.loads(src_text)
    except json.JSONDecodeError as exc:
        raise PortableConfigError(f"Source JSON invalid: {src}") from exc

    if not isinstance(src_data, dict):
        raise PortableConfigError(f"Source JSON root must be object: {src}")

    rel_path = str(dst.relative_to(project_root))

    if not dst.exists():
        _ensure_parent(dst)
        dst.write_text(json.dumps(src_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        txn_changes.append(
            {
                "path": rel_path,
                "operation": "created",
                "backup": None,
                "action_id": action_id,
            }
        )
        return

    target_text = dst.read_text(encoding="utf-8")
    try:
        target_data = json.loads(target_text)
    except json.JSONDecodeError:
        conflict_file = conflict_root / rel_path.replace("/", "__")
        conflict_file.parent.mkdir(parents=True, exist_ok=True)
        conflict_file.write_text(json.dumps(src_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        txn_conflicts.append(
            {
                "path": rel_path,
                "reason": "target_json_invalid",
                "suggested_source": str(conflict_file.relative_to(project_root)),
            }
        )
        return

    if not isinstance(target_data, dict):
        raise PortableConfigError(f"Target JSON root must be object: {rel_path}")

    merged = copy.deepcopy(target_data)
    changed = _merge_missing(merged, src_data)
    if not changed:
        return

    backup_rel = _backup_file(project_root=project_root, file_path=dst, backup_root=backup_root)
    dumped = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    dst.write_text(dumped, encoding="utf-8")
    txn_changes.append(
        {
            "path": rel_path,
            "operation": "updated",
            "backup": backup_rel,
            "action_id": action_id,
        }
    )


def _sync_additive_dir(
    *,
    action_id: str,
    src_dir: pathlib.Path,
    dst_dir: pathlib.Path,
    project_root: pathlib.Path,
    backup_root: pathlib.Path,
    txn_changes: list[dict[str, Any]],
) -> None:
    if not src_dir.exists() or not src_dir.is_dir():
        raise PortableConfigError(f"Source directory not found: {src_dir}")

    for src in sorted(src_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        rel_path = str(dst.relative_to(project_root))
        _ensure_parent(dst)

        if not dst.exists():
            shutil.copy2(src, dst)
            txn_changes.append(
                {
                    "path": rel_path,
                    "operation": "created",
                    "backup": None,
                    "action_id": action_id,
                }
            )
            continue

        if _hash_bytes(src) == _hash_bytes(dst):
            continue

        backup_rel = _backup_file(project_root=project_root, file_path=dst, backup_root=backup_root)
        shutil.copy2(src, dst)
        txn_changes.append(
            {
                "path": rel_path,
                "operation": "updated",
                "backup": backup_rel,
                "action_id": action_id,
            }
        )


def apply_profile(
    *,
    project_root: pathlib.Path,
    template_root: pathlib.Path,
    profile_name: str,
    namespace: str,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    template_root = template_root.resolve()

    profile, manifest = load_profile_and_manifest(template_root, profile_name)
    targets = profile.get("targets", {})
    state_cfg = profile.get("state", {})

    state_path = project_root / state_cfg.get("state_file", ".codex/portable/state.json")
    backup_base = project_root / state_cfg.get("backup_dir", ".codex/portable/backups")
    history_dir = project_root / state_cfg.get("history_dir", ".codex/portable/history")
    conflicts_base = project_root / state_cfg.get("conflicts_dir", ".codex/portable/conflicts")

    txn_id = _new_txn_id()
    backup_root = backup_base / txn_id
    conflict_root = conflicts_base / txn_id

    txn_changes: list[dict[str, Any]] = []
    txn_conflicts: list[dict[str, Any]] = []
    current_action_id = "<init>"

    try:
        for action in manifest["actions"]:
            action_id = action["id"]
            current_action_id = action_id
            src = template_root / action["src"]
            target_key = action["target"]
            strategy = action["strategy"]

            if target_key not in targets:
                raise PortableConfigError(f"Unknown target '{target_key}' in action '{action_id}'")

            dst_rel = _format_target(str(targets[target_key]), namespace)
            dst = project_root / dst_rel

            if strategy == "append_block":
                _append_block(
                    action_id=action_id,
                    src=src,
                    dst=dst,
                    namespace=namespace,
                    project_root=project_root,
                    backup_root=backup_root,
                    txn_changes=txn_changes,
                )
            elif strategy == "merge_toml_keys":
                _merge_toml_keys(
                    action_id=action_id,
                    src=src,
                    dst=dst,
                    project_root=project_root,
                    backup_root=backup_root,
                    conflict_root=conflict_root,
                    txn_changes=txn_changes,
                    txn_conflicts=txn_conflicts,
                )
            elif strategy == "sync_additive_dir":
                _sync_additive_dir(
                    action_id=action_id,
                    src_dir=src,
                    dst_dir=dst,
                    project_root=project_root,
                    backup_root=backup_root,
                    txn_changes=txn_changes,
                )
            elif strategy == "merge_json_keys":
                _merge_json_keys(
                    action_id=action_id,
                    src=src,
                    dst=dst,
                    project_root=project_root,
                    backup_root=backup_root,
                    conflict_root=conflict_root,
                    txn_changes=txn_changes,
                    txn_conflicts=txn_conflicts,
                )
            else:
                raise PortableConfigError(f"Unsupported strategy: {strategy}")
    except Exception as exc:
        try:
            _restore_changes(
                project_root=project_root,
                changes=txn_changes,
            )
        except Exception as rollback_exc:
            raise PortableConfigError(
                f"Apply failed at action '{current_action_id}', auto-rollback failed: {rollback_exc}"
            ) from exc

        shutil.rmtree(backup_root, ignore_errors=True)
        shutil.rmtree(conflict_root, ignore_errors=True)
        _remove_empty_parents(backup_base, project_root)
        _remove_empty_parents(conflicts_base, project_root)
        _remove_empty_parents(project_root / ".codex" / "portable", project_root)

        raise PortableConfigError(f"Apply failed at action '{current_action_id}': {exc}") from exc

    state = _load_state(state_path)
    transaction = {
        "txn_id": txn_id,
        "kind": "apply",
        "created_at": _utc_now_iso(),
        "profile": profile_name,
        "namespace": namespace,
        "template_root": str(template_root),
        "rolled_back": False,
        "changes": txn_changes,
        "conflicts": txn_conflicts,
    }
    state.setdefault("transactions", []).append(transaction)
    _save_state(state_path, state)

    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"apply-{txn_id}.json"
    history_path.write_text(json.dumps(transaction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "txn_id": txn_id,
        "changes": len(txn_changes),
        "conflicts": len(txn_conflicts),
        "state_file": str(state_path.relative_to(project_root)),
    }


def _latest_open_apply_transaction(state: dict[str, Any]) -> dict[str, Any] | None:
    for txn in reversed(state.get("transactions", [])):
        if txn.get("kind") == "apply" and not txn.get("rolled_back", False):
            return txn
    return None


def _remove_empty_parents(path: pathlib.Path, stop: pathlib.Path) -> None:
    current = path
    while current != stop and current.exists():
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _restore_changes(
    *,
    project_root: pathlib.Path,
    changes: list[dict[str, Any]],
) -> tuple[int, int]:
    restored = 0
    removed = 0

    for change in reversed(changes):
        rel_path = change["path"]
        file_path = project_root / rel_path
        op = change.get("operation")

        if op == "created":
            if file_path.exists():
                file_path.unlink()
                removed += 1
                _remove_empty_parents(file_path.parent, project_root)
            continue

        if op == "updated":
            backup_rel = change.get("backup")
            if not backup_rel:
                raise PortableConfigError(f"Missing backup for updated file: {rel_path}")
            backup_path = project_root / backup_rel
            if not backup_path.exists():
                raise PortableConfigError(f"Backup file missing: {backup_rel}")
            _ensure_parent(file_path)
            shutil.copy2(backup_path, file_path)
            restored += 1
            continue

        raise PortableConfigError(f"Unsupported change operation: {op}")

    return restored, removed


def rollback_transaction(
    *,
    project_root: pathlib.Path,
    txn_id: str | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    state_path = project_root / ".codex" / "portable" / "state.json"
    history_dir = project_root / ".codex" / "portable" / "history"

    state = _load_state(state_path)
    txns: list[dict[str, Any]] = state.get("transactions", [])

    target_txn: dict[str, Any] | None = None
    if txn_id:
        for txn in txns:
            if txn.get("kind") == "apply" and txn.get("txn_id") == txn_id:
                target_txn = txn
                break
        if target_txn is None:
            raise PortableConfigError(f"Transaction not found: {txn_id}")
        if target_txn.get("rolled_back", False):
            raise PortableConfigError(f"Transaction already rolled back: {txn_id}")
    else:
        target_txn = _latest_open_apply_transaction(state)
        if target_txn is None:
            raise PortableConfigError("No rollback candidate found")

    restored, removed = _restore_changes(
        project_root=project_root,
        changes=target_txn.get("changes", []),
    )

    target_txn["rolled_back"] = True
    target_txn["rolled_back_at"] = _utc_now_iso()

    rollback_id = _new_txn_id()
    rollback_event = {
        "txn_id": rollback_id,
        "kind": "rollback",
        "rollback_of": target_txn["txn_id"],
        "created_at": _utc_now_iso(),
        "restored": restored,
        "removed": removed,
    }
    txns.append(rollback_event)

    _save_state(state_path, state)

    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"rollback-{rollback_id}.json"
    history_path.write_text(json.dumps(rollback_event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "rollback_txn": rollback_id,
        "rollback_of": target_txn["txn_id"],
        "restored": restored,
        "removed": removed,
        "state_file": str(state_path.relative_to(project_root)),
    }
