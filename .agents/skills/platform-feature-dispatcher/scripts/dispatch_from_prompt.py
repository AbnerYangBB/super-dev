#!/usr/bin/env python3
"""Convert natural language request to intent and generate templates."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shlex
import sys
from typing import Any


class PromptParseError(RuntimeError):
    """Raised when prompt intent cannot be safely parsed."""


def _stable_intent_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _extract_platform_targets(text: str, lowered: str) -> list[str]:
    has_codex_only = bool(
        re.search(
            r"(仅|只(?:给|在)?|only)\s*(?:支持\s*)?(?:codex(?:\s*cli)?|codex-cli)",
            text,
            flags=re.IGNORECASE,
        )
    ) or "codex only" in lowered
    has_claude_only = bool(
        re.search(
            r"(仅|只(?:给|在)?|only)\s*(?:支持\s*)?(?:claude(?:\s*code)?|claude-code)",
            text,
            flags=re.IGNORECASE,
        )
    ) or "claude only" in lowered
    has_trae_only = bool(
        re.search(
            r"(仅|只(?:给|在)?|only)\s*(?:支持\s*)?(?:trae(?:\s*ide)?|trae-ide)",
            text,
            flags=re.IGNORECASE,
        )
    ) or "trae only" in lowered

    if has_codex_only and not has_claude_only and not has_trae_only:
        return ["codex-cli"]
    if has_claude_only and not has_codex_only and not has_trae_only:
        return ["claude-code"]
    if has_trae_only and not has_codex_only and not has_claude_only:
        return ["trae-ide"]
    return ["claude-code", "codex-cli", "trae-ide"]


def _strip_platform_clause(value: str) -> str:
    value = re.split(
        r"\s+(?:仅|只(?:给|在)?|only)\s+(?:claude|codex|trae).*",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return value.strip().rstrip("，,。.;；")


def _extract_mcp_server(text: str, lowered: str) -> dict[str, Any]:
    name_match = re.search(
        r"(?:mcp\s*server|server)\s*[:：]\s*([a-zA-Z0-9._-]+)",
        text,
        flags=re.IGNORECASE,
    ) or re.search(
        r"(?:mcp\s*server|server)\s+([a-zA-Z0-9._-]+)",
        text,
        flags=re.IGNORECASE,
    )
    name = (name_match.group(1) if name_match else "example-server").strip()

    command_match = re.search(r"command\s*[:：]\s*([^\s,，;；]+)", text, flags=re.IGNORECASE)
    command = command_match.group(1).strip() if command_match else "npx"

    args_match = re.search(r"args?\s*[:：]\s*(.+)$", text, flags=re.IGNORECASE)
    if args_match:
        raw_args = _strip_platform_clause(args_match.group(1))
        args = shlex.split(raw_args)
    else:
        pkg = "example-mcp-server" if name == "example-server" else name
        args = ["-y", pkg]

    return {
        "name": name,
        "command": command,
        "args": args,
    }


def _extract_hook_command(text: str, lowered: str) -> str:
    command_match = re.search(r"command\s*[:：]\s*(.+)$", text, flags=re.IGNORECASE)
    if command_match:
        return _strip_platform_clause(command_match.group(1))

    if "sync-add-ios-loc" in lowered:
        return "echo run sync-add-ios-loc"
    return "echo run custom-hook"


def _check_unsupported_remove_semantics(text: str, lowered: str) -> None:
    remove_keywords = ("删除", "移除", "remove", "delete")
    if any(keyword in text or keyword in lowered for keyword in remove_keywords):
        raise PromptParseError("当前不支持删除语义（删除/移除/remove/delete），请手工修改 intent。")


def _build_intent_from_prompt(prompt: str) -> dict[str, Any]:
    text = prompt.strip()
    lowered = text.lower()
    _check_unsupported_remove_semantics(text, lowered)
    platform_targets = _extract_platform_targets(text, lowered)

    intent: dict[str, Any] = {
        "id": "generated_intent",
        "feature_type": "instruction",
        "trigger": "always",
        "tool_ref": "instruction:custom",
        "desired_behavior": text,
        "platform_targets": platform_targets,
        "constraints": [
            "only_touch_ai_config",
            "preserve_user_existing_config",
        ],
        "metadata": {
            "source": "platform-feature-dispatcher",
            "original_prompt": text,
        },
    }

    if "hook" in lowered:
        intent["feature_type"] = "hook"
        intent["trigger"] = "pre_commit" if ("提交前" in text or "pre-commit" in lowered or "pre_commit" in lowered) else "always"
        intent["metadata"]["hook_command"] = _extract_hook_command(text, lowered)
        if "sync-add-ios-loc" in lowered:
            intent["tool_ref"] = "skill:sync-add-ios-loc"
            intent["desired_behavior"] = "validate localization before commit"
            intent["id"] = _stable_intent_id("hook_sync_add_ios_loc", text)
        else:
            intent["tool_ref"] = "hook:custom"
            intent["id"] = _stable_intent_id("hook_custom", text)
        return intent

    if "mcp" in lowered:
        mcp_server = _extract_mcp_server(text, lowered)
        intent["feature_type"] = "mcp"
        intent["tool_ref"] = f"mcp:{mcp_server['name']}"
        intent["metadata"]["mcp_server"] = mcp_server
        intent["id"] = _stable_intent_id("mcp_custom", text)
        return intent

    if "skill" in lowered:
        intent["feature_type"] = "skill"
        skill_match = re.search(r"skill[:：\s]+([a-zA-Z0-9_-]+)", lowered)
        skill_name = skill_match.group(1) if skill_match else "custom-skill"
        intent["tool_ref"] = f"skill:{skill_name}"
        intent["id"] = _stable_intent_id(f"skill_{skill_name.replace('-', '_')}", text)
        return intent

    intent["id"] = _stable_intent_id("instruction_custom", text)
    return intent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch feature request from natural language prompt")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--prompt", required=True, help="Natural language feature request")
    parser.add_argument("--dry-run", action="store_true", help="Do not write templates")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = pathlib.Path(args.repo_root).resolve()

    scripts_dir = repo_root / "common" / "install" / "scripts"
    sys.path.insert(0, str(scripts_dir))

    from portable_dispatch import dispatch_intent, load_capability_matrix
    from portable_generate_templates import apply_actions

    try:
        intent = _build_intent_from_prompt(args.prompt)
    except PromptParseError as exc:
        error_payload = {
            "status": "error",
            "message": str(exc),
            "prompt": args.prompt,
        }
        if args.pretty:
            print(json.dumps(error_payload, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(json.dumps(error_payload, ensure_ascii=False), file=sys.stderr)
        return 1

    matrix = load_capability_matrix(repo_root)
    actions = dispatch_intent(intent, matrix)
    changes = apply_actions(
        repo_root=repo_root,
        intent_id=intent["id"],
        actions=actions,
        dry_run=args.dry_run,
    )

    generated_dir = repo_root / "common" / "platforms" / "intents" / "generated"
    generated_path = generated_dir / f"{intent['id']}.json"
    if not args.dry_run:
        generated_dir.mkdir(parents=True, exist_ok=True)
        generated_path.write_text(json.dumps(intent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "status": "ok",
        "dry_run": args.dry_run,
        "intent": intent,
        "actions": actions,
        "changes": changes,
        "generated_intent_file": str(generated_path.relative_to(repo_root)),
    }

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
