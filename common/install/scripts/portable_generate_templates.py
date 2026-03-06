#!/usr/bin/env python3
"""Generate platform templates from a normalized intent."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import tomllib
from typing import Any

from portable_dispatch import dispatch_intent, load_capability_matrix, load_json


class TemplateGenerationError(RuntimeError):
    """Raised when template generation fails."""


def _ensure_parent(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> bool:
    changed = False
    for key, value in source.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
            changed = True
            continue
        if isinstance(target[key], dict) and isinstance(value, dict):
            if _merge_missing(target[key], value):
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
    raise TemplateGenerationError(f"Unsupported TOML value type: {type(value)!r}")


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
            next_prefix = subkey if prefix is None else f"{prefix}.{subkey}"
            emit_table(subtable, next_prefix)
            if idx != len(subtables) - 1:
                lines.append("")

    emit_table(data, None)
    return "\n".join(lines).strip() + "\n"


def _resolve_template_path(repo_root: pathlib.Path, platform: str, target: str, domain: str) -> pathlib.Path:
    domain_root = "web" if domain == "web" else "ios"
    if platform == "codex-cli":
        mapping = {
            "AGENTS.md": repo_root / domain_root / "codex" / "AGENTS.md",
            ".codex/config.toml": repo_root / domain_root / "codex" / "config.toml",
            ".agents/skills": repo_root / domain_root / "skills",
        }
    elif platform == "claude-code":
        mapping = {
            "CLAUDE.md": repo_root / domain_root / "claude" / "CLAUDE.md",
            ".claude/settings.json": repo_root / domain_root / "claude" / "settings.json",
            ".mcp.json": repo_root / domain_root / "claude" / "mcp.json",
            ".claude/skills": repo_root / domain_root / "skills",
        }
    elif platform == "trae-ide":
        mapping = {
            ".trae/rules/super-dev-rules.md": repo_root / domain_root / "trae" / "RULES.md",
            ".trae/skills": repo_root / domain_root / "skills",
            "mcp.json": repo_root / domain_root / "trae" / "mcp.json",
        }
    else:
        raise TemplateGenerationError(f"Unsupported platform: {platform}")

    if target not in mapping:
        raise TemplateGenerationError(f"Unsupported target for {platform}: {target}")
    return mapping[target]


def _append_managed_block(file_path: pathlib.Path, block_id: str, body: str, dry_run: bool) -> bool:
    begin = f"# BEGIN SUPER-DEV DISPATCH:{block_id}"
    end = f"# END SUPER-DEV DISPATCH:{block_id}"
    managed = f"{begin}\n{body.strip()}\n{end}\n"

    old = file_path.read_text(encoding="utf-8") if file_path.exists() else ""

    if begin in old and end in old:
        start = old.index(begin)
        stop = old.index(end, start) + len(end)
        suffix = old[stop:]
        if suffix.startswith("\n"):
            suffix = suffix[1:]
        new_text = old[:start].rstrip("\n") + "\n\n" + managed + suffix
    else:
        new_text = (old.rstrip("\n") + "\n\n" if old else "") + managed

    if new_text == old:
        return False

    if not dry_run:
        _ensure_parent(file_path)
        file_path.write_text(new_text, encoding="utf-8")
    return True


def _merge_json_file(file_path: pathlib.Path, payload: dict[str, Any], dry_run: bool) -> bool:
    old_data: dict[str, Any]
    if file_path.exists():
        old_data = json.loads(file_path.read_text(encoding="utf-8"))
    else:
        old_data = {}

    merged = copy.deepcopy(old_data)
    changed = _merge_missing(merged, payload)
    if not changed:
        return False

    if not dry_run:
        _ensure_parent(file_path)
        file_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _merge_toml_file(file_path: pathlib.Path, payload: dict[str, Any], dry_run: bool) -> bool:
    old_data: dict[str, Any]
    if file_path.exists():
        old_data = tomllib.loads(file_path.read_text(encoding="utf-8"))
    else:
        old_data = {}

    merged = copy.deepcopy(old_data)
    changed = _merge_missing(merged, payload)
    if not changed:
        return False

    if not dry_run:
        _ensure_parent(file_path)
        file_path.write_text(_toml_dump(merged), encoding="utf-8")
    return True


def apply_actions(
    *,
    repo_root: pathlib.Path,
    intent_id: str,
    actions: dict[str, list[dict[str, Any]]],
    dry_run: bool,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    for platform, platform_actions in actions.items():
        for idx, action in enumerate(platform_actions):
            op = action["operation"]
            target = action["target"]
            payload = action.get("payload", {})
            domain = str(action.get("domain", intent_id.split("_", 1)[0] if "_" in intent_id else "ios"))

            if op == "sync_additive_dir":
                # 该操作属于模板外部下发动作，生成阶段无需改动 ios/skills 原始目录。
                continue

            template_path = _resolve_template_path(repo_root, platform, target, domain)
            changed = False

            if op == "append_block":
                instruction = payload.get("instruction", "")
                block_id = f"{intent_id}:{platform}:{idx}" if domain == "ios" else f"{domain}:{intent_id}:{platform}:{idx}"
                changed = _append_managed_block(template_path, block_id, instruction, dry_run)
            elif op == "merge_json_keys":
                changed = _merge_json_file(template_path, payload, dry_run)
            elif op == "merge_toml_keys":
                changed = _merge_toml_file(template_path, payload, dry_run)
            else:
                raise TemplateGenerationError(f"Unsupported operation: {op}")

            if changed:
                changes.append(
                    {
                        "platform": platform,
                        "operation": op,
                        "target": target,
                        "template_path": str(template_path.relative_to(repo_root)),
                    }
                )

    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate templates from intent")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--intent-file", required=True, help="Path to intent JSON")
    parser.add_argument("--dry-run", action="store_true", help="Calculate changes without writing files")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = pathlib.Path(args.repo_root).resolve()
    intent = load_json(pathlib.Path(args.intent_file).resolve())
    matrix = load_capability_matrix(repo_root)
    actions = dispatch_intent(intent, matrix)

    changes = apply_actions(
        repo_root=repo_root,
        intent_id=str(intent.get("id", "intent")),
        actions=actions,
        dry_run=args.dry_run,
    )

    payload = {
        "status": "ok",
        "intent_id": intent.get("id"),
        "dry_run": args.dry_run,
        "changes": changes,
        "actions": actions,
    }

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
