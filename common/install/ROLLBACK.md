# Portable AI Config ROLLBACK

## Purpose
回退由 portable installer 产生的配置变更。

## Inputs
1. `txn_id`：可选，默认 `latest`。
2. `project_root`：默认当前目录。

## Hard Rules
1. 回退仅根据 `.codex/portable/state.json` 与备份执行。
2. 仅恢复/删除 AI 配置相关文件。
3. 找不到可回退事务时必须报错，不允许猜测恢复。

## One-Click (AI)
在目标项目中，让 AI 执行：

```text
Fetch and follow instructions from <RAW_BASE_URL>/common/install/ROLLBACK.md and rollback latest transaction
```

## Rollback latest
在目标项目根目录执行：

```bash
set -euo pipefail

TEMPLATE_DIR=".codex/portable/template/super-dev"
PROJECT_ROOT="$(pwd)"

python3 "$TEMPLATE_DIR/common/install/scripts/portable_rollback.py" \
  --project-root "$PROJECT_ROOT"
```

## Rollback 指定事务

```bash
set -euo pipefail

TEMPLATE_DIR=".codex/portable/template/super-dev"
PROJECT_ROOT="$(pwd)"
TXN_ID="<txn-id>"

python3 "$TEMPLATE_DIR/common/install/scripts/portable_rollback.py" \
  --project-root "$PROJECT_ROOT" \
  --txn-id "$TXN_ID"
```

## Expected Output
成功时应输出 JSON，包含：
1. `status=ok`
2. `rollback_of`
3. `restored` / `removed`
4. `state_file=.codex/portable/state.json`
