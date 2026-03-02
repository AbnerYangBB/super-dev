#!/usr/bin/env python3
"""Compile a normalized feature intent to per-platform actions."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


class DispatchError(RuntimeError):
    """Raised when intent or capability matrix is invalid."""


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_capability_matrix(repo_root: pathlib.Path) -> dict[str, dict[str, dict[str, Any]]]:
    cap_dir = repo_root / "common" / "platforms" / "capabilities"
    files = ("claude-code.json", "codex-cli.json")

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for filename in files:
        payload = load_json(cap_dir / filename)
        platform = payload["platform"]
        matrix[platform] = {}
        for item in payload["capabilities"]:
            matrix[platform][item["id"]] = item
    return matrix


def _memory_target(platform: str) -> str:
    if platform == "claude-code":
        return "CLAUDE.md"
    if platform == "codex-cli":
        return "AGENTS.md"
    raise DispatchError(f"Unsupported platform: {platform}")


def _skill_target(platform: str) -> str:
    if platform == "claude-code":
        return ".claude/skills"
    if platform == "codex-cli":
        return ".agents/skills"
    raise DispatchError(f"Unsupported platform: {platform}")


def _build_instruction_line(intent: dict[str, Any]) -> str:
    trigger = intent.get("trigger", "always")
    tool_ref = intent.get("tool_ref", "")
    behavior = intent.get("desired_behavior", "")
    return f"[{trigger}] {tool_ref}: {behavior}".strip()


def _resolve_hook_command(intent: dict[str, Any]) -> str:
    metadata = intent.get("metadata", {})
    if isinstance(metadata, dict):
        command = metadata.get("hook_command")
        if isinstance(command, str) and command.strip():
            return command.strip()

    tool_ref = str(intent.get("tool_ref", ""))
    if tool_ref == "skill:sync-add-ios-loc":
        return "echo run sync-add-ios-loc"
    return "echo run custom-hook"


def _resolve_mcp_server_payload(intent: dict[str, Any]) -> dict[str, Any]:
    metadata = intent.get("metadata", {})
    if isinstance(metadata, dict):
        mcp_server = metadata.get("mcp_server")
        if isinstance(mcp_server, dict):
            name = mcp_server.get("name")
            command = mcp_server.get("command")
            args = mcp_server.get("args")
            if isinstance(name, str) and name and isinstance(command, str) and command:
                if isinstance(args, list) and all(isinstance(item, str) for item in args):
                    return {
                        "name": name,
                        "command": command,
                        "args": args,
                    }

    return {
        "name": "example-server",
        "command": "npx",
        "args": ["-y", "example-mcp-server"],
    }


def _dispatch_hook(intent: dict[str, Any], platform: str, support: str) -> list[dict[str, Any]]:
    if support == "supported":
        if platform == "claude-code":
            hook_command = _resolve_hook_command(intent)
            return [
                {
                    "operation": "merge_json_keys",
                    "target": ".claude/settings.json",
                    "capability": "hooks",
                    "payload": {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash(git commit:*)",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": hook_command,
                                        }
                                    ],
                                }
                            ]
                        }
                    },
                }
            ]

    return [
        {
            "operation": "append_block",
            "target": _memory_target(platform),
            "capability": "hooks",
            "payload": {
                "instruction": _build_instruction_line(intent),
                "fallback_reason": "hooks_not_supported_or_not_documented",
            },
        }
    ]


def _dispatch_instruction(intent: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    return [
        {
            "operation": "append_block",
            "target": _memory_target(platform),
            "capability": "instruction",
            "payload": {
                "instruction": _build_instruction_line(intent),
            },
        }
    ]


def _dispatch_skill(intent: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    return [
        {
            "operation": "sync_additive_dir",
            "target": _skill_target(platform),
            "capability": "skills",
            "payload": {
                "tool_ref": intent.get("tool_ref"),
            },
        }
    ]


def _dispatch_mcp(intent: dict[str, Any], platform: str, support: str) -> list[dict[str, Any]]:
    if support != "supported":
        return _dispatch_instruction(intent, platform)

    mcp_server = _resolve_mcp_server_payload(intent)

    if platform == "claude-code":
        return [
            {
                "operation": "merge_json_keys",
                "target": ".mcp.json",
                "capability": "mcp",
                "payload": {
                    "mcpServers": {
                        mcp_server["name"]: {
                            "command": mcp_server["command"],
                            "args": mcp_server["args"],
                        }
                    }
                },
            }
        ]

    if platform == "codex-cli":
        return [
            {
                "operation": "merge_toml_keys",
                "target": ".codex/config.toml",
                "capability": "mcp",
                "payload": {
                    "mcp_servers": {
                        mcp_server["name"]: {
                            "command": mcp_server["command"],
                            "args": mcp_server["args"],
                        }
                    }
                },
            }
        ]

    raise DispatchError(f"Unsupported platform: {platform}")


def dispatch_intent(
    intent: dict[str, Any],
    capability_matrix: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    feature_type = intent.get("feature_type")
    if not feature_type:
        raise DispatchError("Intent missing feature_type")

    targets = intent.get("platform_targets")
    if not isinstance(targets, list) or not targets:
        raise DispatchError("Intent missing platform_targets")

    out: dict[str, list[dict[str, Any]]] = {}

    for platform in targets:
        if platform not in capability_matrix:
            raise DispatchError(f"Unknown platform: {platform}")

        platform_caps = capability_matrix[platform]

        if feature_type == "hook":
            support = platform_caps.get("hooks", {}).get("support", "unsupported")
            out[platform] = _dispatch_hook(intent, platform, support)
        elif feature_type == "instruction":
            out[platform] = _dispatch_instruction(intent, platform)
        elif feature_type == "skill":
            out[platform] = _dispatch_skill(intent, platform)
        elif feature_type == "mcp":
            support = platform_caps.get("mcp", {}).get("support", "unsupported")
            out[platform] = _dispatch_mcp(intent, platform, support)
        elif feature_type == "settings":
            out[platform] = _dispatch_instruction(intent, platform)
        else:
            raise DispatchError(f"Unsupported feature_type: {feature_type}")

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile intent to platform actions")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--intent-file", required=True, help="Path to intent JSON file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = pathlib.Path(args.repo_root).resolve()
    intent = load_json(pathlib.Path(args.intent_file).resolve())
    matrix = load_capability_matrix(repo_root)
    actions = dispatch_intent(intent, matrix)
    payload = {
        "intent_id": intent.get("id"),
        "actions": actions,
    }
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
