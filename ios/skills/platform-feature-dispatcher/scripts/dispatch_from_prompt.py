#!/usr/bin/env python3
"""Convert natural language request to intent and generate templates."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


def _build_intent_from_prompt(prompt: str) -> dict[str, Any]:
    text = prompt.strip()
    lowered = text.lower()

    intent: dict[str, Any] = {
        "id": "generated_intent",
        "feature_type": "instruction",
        "trigger": "always",
        "tool_ref": "instruction:custom",
        "desired_behavior": text,
        "platform_targets": ["claude-code", "codex-cli"],
        "constraints": [
            "only_touch_ai_config",
            "preserve_user_existing_config",
        ],
        "metadata": {
            "source": "platform-feature-dispatcher",
        },
    }

    if "hook" in lowered:
        intent["feature_type"] = "hook"
        intent["trigger"] = "pre_commit" if ("提交前" in text or "pre-commit" in lowered or "pre_commit" in lowered) else "always"
        if "sync-add-ios-loc" in lowered:
            intent["tool_ref"] = "skill:sync-add-ios-loc"
            intent["desired_behavior"] = "validate localization before commit"
            intent["id"] = "ios_loc_pre_commit_check"
        else:
            intent["tool_ref"] = "hook:custom"
            intent["id"] = "custom_hook_check"
        return intent

    if "mcp" in lowered:
        intent["feature_type"] = "mcp"
        intent["tool_ref"] = "mcp:custom"
        intent["id"] = "custom_mcp_integration"
        return intent

    if "skill" in lowered:
        intent["feature_type"] = "skill"
        skill_match = re.search(r"skill[:：\s]+([a-zA-Z0-9_-]+)", lowered)
        skill_name = skill_match.group(1) if skill_match else "custom-skill"
        intent["tool_ref"] = f"skill:{skill_name}"
        intent["id"] = f"sync_{skill_name.replace('-', '_')}"
        return intent

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

    intent = _build_intent_from_prompt(args.prompt)
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
