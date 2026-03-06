# Portable AI Config ROLLBACK

## Purpose
回退由 portable installer 产生的配置变更。

## Inputs
1. `txn_id`：可选，默认 `latest`。
2. `project_root`：默认当前目录。
3. `SUPER_DEV_HOME`：可选，默认 `$HOME/.super-dev`。

模板默认目录：`$HOME/.super-dev/templates/super-dev`。

## Hard Rules
1. 回退仅根据事务 `state.json` 与备份执行（支持 `.codex/portable/state.json`、`.claude/portable/state.json`、`.trae/portable/state.json`）。
2. 仅恢复/删除 AI 配置相关文件。
3. 找不到可回退事务时必须报错，不允许猜测恢复。
4. 若同一项目同时安装了 iOS 与 web，默认只回退最近一次安装事务，不会连带回退更早的平台事务。

## One-Click (AI)
在目标项目中，让 AI 执行：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md and rollback latest transaction
```

## Rollback latest
在目标项目根目录执行：

```bash
set -euo pipefail

SUPER_DEV_HOME="${SUPER_DEV_HOME:-$HOME/.super-dev}"
TEMPLATE_DIR="$SUPER_DEV_HOME/templates/super-dev"
PROJECT_ROOT="$(pwd)"

python3 "$TEMPLATE_DIR/common/install/scripts/portable_rollback.py" \
  --project-root "$PROJECT_ROOT"
```

## Rollback 指定事务

```bash
set -euo pipefail

SUPER_DEV_HOME="${SUPER_DEV_HOME:-$HOME/.super-dev}"
TEMPLATE_DIR="$SUPER_DEV_HOME/templates/super-dev"
PROJECT_ROOT="$(pwd)"
TXN_ID="<txn-id>"

python3 "$TEMPLATE_DIR/common/install/scripts/portable_rollback.py" \
  --project-root "$PROJECT_ROOT" \
  --txn-id "$TXN_ID"
```

## Fork Local Template Flow
如果你使用的是本地 fork 模板，也可以直接执行：

```bash
python3 /path/to/your-fork/common/install/scripts/portable_rollback.py \
  --project-root "$(pwd)"
```

## Expected Output
成功时应输出 JSON，包含：
1. `status=ok`
2. `rollback_of`
3. `restored` / `removed`
4. `state_file`（实际回退所用的状态文件路径）
