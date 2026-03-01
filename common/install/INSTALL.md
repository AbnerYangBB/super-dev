# Portable AI Config INSTALL

## Purpose
将本仓库的 AI 模板（`codex-ios` / `claude-ios`）安装到当前项目，并保证：
1. 仅允许修改 AI 配置文件。
2. 不直接替换用户已有配置。
3. 支持后续一键回退。

## Inputs
1. `profile`：默认 `codex-ios`，可选 `claude-ios`。
2. `namespace`：默认 `super-dev`。
3. `project_root`：默认当前目录。
4. `SUPER_DEV_HOME`：可选，默认 `$HOME/.super-dev`。

## Hard Rules
1. 仅允许修改 AI 配置文件，禁止改动业务代码。
2. 先备份后写入；失败必须中止并返回错误。
3. `AGENTS.md` 使用受管区块追加，不整文件覆盖。
4. `.codex/config.toml` 仅补充缺失 key，保留用户已有值。
5. `CLAUDE.md` 使用受管区块追加，不整文件覆盖。
6. `.claude/settings.json` 仅补充缺失 key，保留用户已有值。
7. `.mcp.json` 仅补充缺失 key，保留用户已有 MCP 配置。
8. Codex skills 仅写入 `.agents/skills/<namespace>/`，不触碰其他命名空间。
9. Claude skills 仅写入 `.claude/skills/<namespace>/`，不触碰其他命名空间。

## One-Click (AI)
在目标项目中，让 AI 执行以下短提示词（推荐）：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project
```

## Private Repo Fallback
如果上面的 `raw.githubusercontent.com` 返回 `404`（私有仓库常见），先拉取模板仓库再让 AI 读取本地文档：

```bash
SUPER_DEV_HOME="${SUPER_DEV_HOME:-$HOME/.super-dev}"
TEMPLATE_DIR="$SUPER_DEV_HOME/templates/super-dev"

mkdir -p "$(dirname "$TEMPLATE_DIR")"
if [ ! -d "$TEMPLATE_DIR/.git" ]; then
  git clone --depth=1 git@github.com:AbnerYangBB/super-dev.git "$TEMPLATE_DIR"
else
  git -C "$TEMPLATE_DIR" pull --ff-only
fi
```

```text
Read and follow instructions from $HOME/.super-dev/templates/super-dev/common/install/INSTALL.md
```

## Execution Commands
在目标项目根目录执行：

```bash
set -euo pipefail

SUPER_DEV_HOME="${SUPER_DEV_HOME:-$HOME/.super-dev}"
TEMPLATE_DIR="$SUPER_DEV_HOME/templates/super-dev"
PROJECT_ROOT="$(pwd)"

mkdir -p "$(dirname "$TEMPLATE_DIR")"
if [ ! -d "$TEMPLATE_DIR/.git" ]; then
  git clone --depth=1 https://github.com/AbnerYangBB/super-dev.git "$TEMPLATE_DIR"
else
  git -C "$TEMPLATE_DIR" pull --ff-only
fi

python3 "$TEMPLATE_DIR/common/install/scripts/portable_apply.py" \
  --project-root "$PROJECT_ROOT" \
  --template-root "$TEMPLATE_DIR" \
  --profile codex-ios \
  --namespace super-dev

# Claude iOS
python3 "$TEMPLATE_DIR/common/install/scripts/portable_apply.py" \
  --project-root "$PROJECT_ROOT" \
  --template-root "$TEMPLATE_DIR" \
  --profile claude-ios \
  --namespace super-dev
```

## Expected Output
成功时应输出 JSON，包含：
1. `status=ok`
2. `txn_id`
3. `state_file`（按 profile）：
   - `codex-ios`: `.codex/portable/state.json`
   - `claude-ios`: `.claude/portable/state.json`

## Installed Targets (codex-ios)
1. `ios/codex/AGENTS.md -> AGENTS.md`
2. `ios/codex/config.toml -> .codex/config.toml`
3. `ios/skills/** -> .agents/skills/super-dev/**`

## Installed Targets (claude-ios)
1. `ios/claude/CLAUDE.md -> CLAUDE.md`
2. `ios/claude/settings.json -> .claude/settings.json`
3. `ios/claude/mcp.json -> .mcp.json`
4. `ios/skills/** -> .claude/skills/super-dev/**`

## Rollback Entry
安装完成后，可执行：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md
```
