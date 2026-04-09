# Super-Dev Skills Sync Install Flow

## Purpose

将本仓库中的 `skills/` 全量同步到当前工作区的：

```text
.agents/skills/super-dev/
```

只允许修改这一路径，不允许改动任何其他文件。

## Inputs

- `project_root`: 当前工作区根目录，默认当前目录
- `repo_url`: `https://github.com/AbnerYangBB/super-dev.git`

## Hard Rules

1. 只允许写入 `project_root/.agents/skills/super-dev/`
2. 不允许修改业务代码或任何其他 AI 配置文件
3. 必须先执行 dry-run，再执行真实同步
4. 同步完成后删除临时 clone 目录
5. 最终必须把 dry-run 和真实同步的 JSON 结果展示出来

## Execution Flow

在目标项目根目录执行以下流程：

```bash
set -euo pipefail

PROJECT_ROOT="$(pwd)"
TMP_DIR="$(mktemp -d)"
REPO_DIR="$TMP_DIR/super-dev"

git clone --depth=1 "https://github.com/AbnerYangBB/super-dev.git" "$REPO_DIR"

python3 "$REPO_DIR/scripts/sync_skills.py" \
  --workspace-root "$PROJECT_ROOT" \
  --dry-run

python3 "$REPO_DIR/scripts/sync_skills.py" \
  --workspace-root "$PROJECT_ROOT"

rm -rf "$TMP_DIR"
```

## Success Criteria

成功时：

1. dry-run 输出 JSON
2. 真实同步输出 JSON
3. 只影响 `.agents/skills/super-dev/`
4. 临时 clone 目录已删除

## Update

更新方式与安装完全相同：重复执行本流程即可。
