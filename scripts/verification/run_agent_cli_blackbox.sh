#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="."
OUTPUT=""
WORK_DIR=""
SKIP_CODEX=0
SKIP_CLAUDE=0
PRETTY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --work-dir)
      WORK_DIR="$2"
      shift 2
      ;;
    --skip-codex)
      SKIP_CODEX=1
      shift
      ;;
    --skip-claude)
      SKIP_CLAUDE=1
      shift
      ;;
    --pretty)
      PRETTY=1
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

if [[ -z "$WORK_DIR" ]]; then
  WORK_DIR="$(mktemp -d)"
else
  mkdir -p "$WORK_DIR"
  WORK_DIR="$(cd "$WORK_DIR" && pwd)"
fi

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="$WORK_DIR/agent-cli-blackbox-report.json"
fi

FORK="$WORK_DIR/super-dev-fork"
TARGET_CODEX="$WORK_DIR/newbie-project-codex"
TARGET_CLAUDE="$WORK_DIR/newbie-project-claude"

cp -R "$REPO_ROOT" "$FORK"
rm -rf "$FORK/.git"
mkdir -p "$TARGET_CODEX" "$TARGET_CLAUDE"
git -C "$TARGET_CODEX" init -q
git -C "$TARGET_CLAUDE" init -q

python3 "$FORK/.agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py" \
  --repo-root "$FORK" \
  --prompt "增加一个 MCP server: lint-server command: uvx args: lint-mcp --stdio" \
  --pretty > "$WORK_DIR/dispatch_mcp.json"

python3 "$FORK/.agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py" \
  --repo-root "$FORK" \
  --prompt "增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验" \
  --pretty > "$WORK_DIR/dispatch_hook.json"

CODEX_INSTALL_EXIT=0
CODEX_UPDATE_EXIT=0
CLAUDE_INSTALL_EXIT=0
CLAUDE_UPDATE_EXIT=0
CODEX_ROLLBACK_EXIT=0
CLAUDE_ROLLBACK_EXIT=0

CODEX_AVAILABLE=1
CLAUDE_AVAILABLE=1
if ! command -v codex >/dev/null 2>&1; then
  CODEX_AVAILABLE=0
fi
if ! command -v claude >/dev/null 2>&1; then
  CLAUDE_AVAILABLE=0
fi

if [[ "$SKIP_CODEX" -eq 0 && "$CODEX_AVAILABLE" -eq 1 ]]; then
  PROMPT_CODEX_INSTALL="Read and follow instructions from $FORK/common/install/INSTALL.md. Install profile codex-ios into current project. Use template root $FORK directly and do not clone anything. Execute required commands and output one-line summary."
  PROMPT_CODEX_UPDATE="Read and follow instructions from $FORK/common/install/INSTALL.md. Re-install profile codex-ios in current project as an update. Use template root $FORK directly and do not clone anything. Execute required commands and output one-line summary."

  set +e
  codex exec -C "$TARGET_CODEX" -s workspace-write --add-dir "$FORK" -- "$PROMPT_CODEX_INSTALL" > "$WORK_DIR/codex_install_out.txt" 2> "$WORK_DIR/codex_install_err.txt"
  CODEX_INSTALL_EXIT=$?
  codex exec -C "$TARGET_CODEX" -s workspace-write --add-dir "$FORK" -- "$PROMPT_CODEX_UPDATE" > "$WORK_DIR/codex_update_out.txt" 2> "$WORK_DIR/codex_update_err.txt"
  CODEX_UPDATE_EXIT=$?
  set -e

  set +e
  python3 "$FORK/common/install/scripts/portable_rollback.py" --project-root "$TARGET_CODEX" > "$WORK_DIR/codex_rollback_out.txt" 2> "$WORK_DIR/codex_rollback_err.txt"
  CODEX_ROLLBACK_EXIT=$?
  set -e
fi

if [[ "$SKIP_CLAUDE" -eq 0 && "$CLAUDE_AVAILABLE" -eq 1 ]]; then
  PROMPT_CLAUDE_INSTALL="Read and follow instructions from $FORK/common/install/INSTALL.md. Install profile claude-ios into current project. Use template root $FORK directly and do not clone anything. Execute required commands and output one-line summary."
  PROMPT_CLAUDE_UPDATE="Read and follow instructions from $FORK/common/install/INSTALL.md. Re-install profile claude-ios in current project as an update. Use template root $FORK directly and do not clone anything. Execute required commands and output one-line summary."

  set +e
  (
    cd "$TARGET_CLAUDE"
    claude -p --permission-mode bypassPermissions --dangerously-skip-permissions --add-dir "$FORK" -- "$PROMPT_CLAUDE_INSTALL"
  ) > "$WORK_DIR/claude_install_out.txt" 2> "$WORK_DIR/claude_install_err.txt"
  CLAUDE_INSTALL_EXIT=$?

  (
    cd "$TARGET_CLAUDE"
    claude -p --permission-mode bypassPermissions --dangerously-skip-permissions --add-dir "$FORK" -- "$PROMPT_CLAUDE_UPDATE"
  ) > "$WORK_DIR/claude_update_out.txt" 2> "$WORK_DIR/claude_update_err.txt"
  CLAUDE_UPDATE_EXIT=$?
  set -e

  set +e
  python3 "$FORK/common/install/scripts/portable_rollback.py" --project-root "$TARGET_CLAUDE" > "$WORK_DIR/claude_rollback_out.txt" 2> "$WORK_DIR/claude_rollback_err.txt"
  CLAUDE_ROLLBACK_EXIT=$?
  set -e
fi

python3 - <<'PY' "$WORK_DIR" "$OUTPUT" "$FORK" "$TARGET_CODEX" "$TARGET_CLAUDE" "$SKIP_CODEX" "$SKIP_CLAUDE" "$CODEX_AVAILABLE" "$CLAUDE_AVAILABLE" "$CODEX_INSTALL_EXIT" "$CODEX_UPDATE_EXIT" "$CLAUDE_INSTALL_EXIT" "$CLAUDE_UPDATE_EXIT" "$CODEX_ROLLBACK_EXIT" "$CLAUDE_ROLLBACK_EXIT" "$PRETTY"
import json
import pathlib
import sys

work = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
fork = pathlib.Path(sys.argv[3])
target_codex = pathlib.Path(sys.argv[4])
target_claude = pathlib.Path(sys.argv[5])
skip_codex = int(sys.argv[6])
skip_claude = int(sys.argv[7])
codex_available = int(sys.argv[8])
claude_available = int(sys.argv[9])
codex_install_exit = int(sys.argv[10])
codex_update_exit = int(sys.argv[11])
claude_install_exit = int(sys.argv[12])
claude_update_exit = int(sys.argv[13])
codex_rollback_exit = int(sys.argv[14])
claude_rollback_exit = int(sys.argv[15])
pretty = int(sys.argv[16])

def read(path: pathlib.Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

def tail(path: pathlib.Path, size: int = 1000) -> str:
    text = read(path)
    return text[-size:]

report = {
    "status": "failed",
    "work_dir": str(work),
    "fork": str(fork),
    "checks": {
        "fork_has_custom_mcp": "lint-server" in read(fork / "ios" / "codex" / "config.toml"),
        "fork_has_hook": "sync-add-ios-loc" in read(fork / "ios" / "codex" / "AGENTS.md"),
    },
    "codex": {
        "enabled": skip_codex == 0 and codex_available == 1,
        "available": bool(codex_available),
        "install_exit": codex_install_exit,
        "update_exit": codex_update_exit,
        "rollback_exit": codex_rollback_exit,
        "targets": {
            "AGENTS.md": (target_codex / "AGENTS.md").exists(),
            ".codex/config.toml": (target_codex / ".codex" / "config.toml").exists(),
            ".agents/skills/super-dev": (target_codex / ".agents" / "skills" / "super-dev").exists(),
            ".codex/portable/state.json": (target_codex / ".codex" / "portable" / "state.json").exists(),
        },
        "output_tail": {
            "install_out": tail(work / "codex_install_out.txt"),
            "install_err": tail(work / "codex_install_err.txt"),
            "update_out": tail(work / "codex_update_out.txt"),
            "update_err": tail(work / "codex_update_err.txt"),
            "rollback_out": tail(work / "codex_rollback_out.txt"),
            "rollback_err": tail(work / "codex_rollback_err.txt"),
        },
    },
    "claude": {
        "enabled": skip_claude == 0 and claude_available == 1,
        "available": bool(claude_available),
        "install_exit": claude_install_exit,
        "update_exit": claude_update_exit,
        "rollback_exit": claude_rollback_exit,
        "targets": {
            "CLAUDE.md": (target_claude / "CLAUDE.md").exists(),
            ".claude/settings.json": (target_claude / ".claude" / "settings.json").exists(),
            ".mcp.json": (target_claude / ".mcp.json").exists(),
            ".claude/skills": (target_claude / ".claude" / "skills").exists(),
            ".claude/portable/state.json": (target_claude / ".claude" / "portable" / "state.json").exists(),
        },
        "output_tail": {
            "install_out": tail(work / "claude_install_out.txt"),
            "install_err": tail(work / "claude_install_err.txt"),
            "update_out": tail(work / "claude_update_out.txt"),
            "update_err": tail(work / "claude_update_err.txt"),
            "rollback_out": tail(work / "claude_rollback_out.txt"),
            "rollback_err": tail(work / "claude_rollback_err.txt"),
        },
    },
}

checks_ok = report["checks"]["fork_has_custom_mcp"] and report["checks"]["fork_has_hook"]

if report["codex"]["enabled"]:
    codex_ok = (
        report["codex"]["install_exit"] == 0
        and report["codex"]["update_exit"] == 0
        and report["codex"]["rollback_exit"] == 0
        and all(report["codex"]["targets"].values())
    )
else:
    codex_ok = True

if report["claude"]["enabled"]:
    claude_ok = (
        report["claude"]["install_exit"] == 0
        and report["claude"]["update_exit"] == 0
        and report["claude"]["rollback_exit"] == 0
        and all(report["claude"]["targets"].values())
    )
else:
    claude_ok = True

report["status"] = "ok" if (checks_ok and codex_ok and claude_ok) else "failed"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if pretty:
    print(json.dumps(report, ensure_ascii=False, indent=2))
else:
    print(json.dumps(report, ensure_ascii=False))
sys.exit(0 if report["status"] == "ok" else 1)
PY
