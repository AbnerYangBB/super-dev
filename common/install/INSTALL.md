# Portable AI Config INSTALL

## Purpose
将本仓库的 AI 模板（`codex-ios` / `claude-ios` / `trae-ios` / `codex-web` / `claude-web` / `trae-web`）安装到当前项目，并保证：
1. 仅允许修改 AI 配置文件。
2. 不直接替换用户已有配置。
3. 支持后续一键回退。
4. 同一 profile 可重复执行用于更新。

## Inputs
1. `profile`：默认 `codex-ios`，可选 `claude-ios` / `trae-ios` / `codex-web` / `claude-web` / `trae-web`。
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
8. Codex skills 仅写入 `.agents/skills/<namespace>/`，不触碰其他目录。
9. Claude skills 仅写入 `.claude/skills/`，不触碰其他目录。
10. Trae rules 仅写入 `.trae/rules/super-dev-rules.md` 的受管区块，不整文件覆盖。
11. `mcp.json` 仅补充缺失 key，保留用户已有 MCP 配置。
12. Trae skills 仅写入 `.trae/skills/`，不触碰其他目录。

## One-Click (AI)
在目标项目中，让 AI 执行以下短提示词（推荐）：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile trae-ios in current project
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-web in current project
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-web in current project
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile trae-web in current project
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

## Fork Local Template Flow (推荐给开发者)
如果你在自己的 fork 中改了模板，推荐直接把 fork 目录作为 `template-root`：

```bash
python3 /path/to/your-fork/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/your-fork" \
  --profile codex-ios \
  --namespace super-dev
```

```bash
python3 /path/to/your-fork/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/your-fork" \
  --profile claude-ios \
  --namespace super-dev
```

```bash
python3 /path/to/your-fork/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/your-fork" \
  --profile trae-ios \
  --namespace super-dev
```

```bash
python3 /path/to/your-fork/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/your-fork" \
  --profile codex-web \
  --namespace super-dev-web
```

```bash
python3 /path/to/your-fork/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/your-fork" \
  --profile claude-web \
  --namespace super-dev-web
```

```bash
python3 /path/to/your-fork/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/your-fork" \
  --profile trae-web \
  --namespace super-dev-web
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

# Trae iOS
python3 "$TEMPLATE_DIR/common/install/scripts/portable_apply.py" \
  --project-root "$PROJECT_ROOT" \
  --template-root "$TEMPLATE_DIR" \
  --profile trae-ios \
  --namespace super-dev

# Codex web
python3 "$TEMPLATE_DIR/common/install/scripts/portable_apply.py" \
  --project-root "$PROJECT_ROOT" \
  --template-root "$TEMPLATE_DIR" \
  --profile codex-web \
  --namespace super-dev-web

# Claude web
python3 "$TEMPLATE_DIR/common/install/scripts/portable_apply.py" \
  --project-root "$PROJECT_ROOT" \
  --template-root "$TEMPLATE_DIR" \
  --profile claude-web \
  --namespace super-dev-web

# Trae web
python3 "$TEMPLATE_DIR/common/install/scripts/portable_apply.py" \
  --project-root "$PROJECT_ROOT" \
  --template-root "$TEMPLATE_DIR" \
  --profile trae-web \
  --namespace super-dev-web
```

## Update Flow
更新流程与安装相同：对同一项目重复执行同 profile 的 `portable_apply.py` 即可。

## Mixed Install Guidance
1. iOS 与 web 可以安装到同一目标项目。
2. 共享目标文件仍只做受管区块追加和缺失 key 合并，不覆盖用户已有配置。
3. 若同一工具同时安装 iOS 与 web，建议使用不同 namespace，例如 `super-dev` 与 `super-dev-web`，减少 skill 目录潜在冲突。
4. 回退默认只回退最近一次事务；若最后执行的是 `codex-web`，则不会自动撤销更早的 `codex-ios`。

## Expected Output
成功时应输出 JSON，包含：
1. `status=ok`
2. `txn_id`
3. `state_file`（按 profile）：
   - `codex-ios`: `.codex/portable/state.json`
   - `claude-ios`: `.claude/portable/state.json`
   - `trae-ios`: `.trae/portable/state.json`
   - `codex-web`: `.codex/portable/state.json`
   - `claude-web`: `.claude/portable/state.json`
   - `trae-web`: `.trae/portable/state.json`

## Installed Targets (codex-ios)
1. `ios/codex/AGENTS.md -> AGENTS.md`
2. `ios/codex/config.toml -> .codex/config.toml`
3. `ios/skills/** -> .agents/skills/super-dev/**`

## Installed Targets (claude-ios)
1. `ios/claude/CLAUDE.md -> CLAUDE.md`
2. `ios/claude/settings.json -> .claude/settings.json`
3. `ios/claude/mcp.json -> .mcp.json`
4. `ios/skills/** -> .claude/skills/**`

## Installed Targets (trae-ios)
1. `ios/trae/RULES.md -> .trae/rules/super-dev-rules.md`
2. `ios/trae/mcp.json -> mcp.json`
3. `ios/skills/** -> .trae/skills/**`

## Installed Targets (codex-web)
1. `web/codex/AGENTS.md -> AGENTS.md`
2. `web/codex/config.toml -> .codex/config.toml`
3. `web/skills/** -> .agents/skills/<namespace>/**`

## Installed Targets (claude-web)
1. `web/claude/CLAUDE.md -> CLAUDE.md`
2. `web/claude/settings.json -> .claude/settings.json`
3. `web/claude/mcp.json -> .mcp.json`
4. `web/skills/** -> .claude/skills/**`

## Installed Targets (trae-web)
1. `web/trae/RULES.md -> .trae/rules/super-dev-rules.md`
2. `web/trae/mcp.json -> mcp.json`
3. `web/skills/** -> .trae/skills/**`

## Rollback Entry
安装完成后，可执行：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md
```
