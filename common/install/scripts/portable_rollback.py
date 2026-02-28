#!/usr/bin/env python3
"""CLI entry for rolling back portable AI config."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from portable_config import PortableConfigError, rollback_transaction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rollback portable AI config")
    parser.add_argument("--project-root", default=".", help="Target project root")
    parser.add_argument("--txn-id", default=None, help="Specific apply txn id to rollback")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = rollback_transaction(
            project_root=pathlib.Path(args.project_root),
            txn_id=args.txn_id,
        )
    except PortableConfigError as exc:
        print(f"portable_rollback error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"status": "ok", **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
