#!/usr/bin/env python3
"""CLI entry for applying portable AI config."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from portable_config import PortableConfigError, apply_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply portable AI config")
    parser.add_argument("--project-root", default=".", help="Target project root")
    parser.add_argument("--template-root", required=True, help="Template repository root")
    parser.add_argument("--profile", default="codex-ios", help="Install profile")
    parser.add_argument("--namespace", default="super-dev", help="Skill namespace directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = apply_profile(
            project_root=pathlib.Path(args.project_root),
            template_root=pathlib.Path(args.template_root),
            profile_name=args.profile,
            namespace=args.namespace,
        )
    except PortableConfigError as exc:
        print(f"portable_apply error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"status": "ok", **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
