# super-dev

可移植的 AI 工程配置仓库，当前聚焦 iOS 开发场景。
项目本身由 AI 自动生成，使用 https://github.com/obra/superpowers skills 框架（建议安装）。

## 状态声明

- 目前仅用于自用。
- 可能存在风险（包含但不限于：提示词行为偏差、安装流程变更、与目标项目配置冲突）。
- 使用前请先在测试项目验证，再应用到正式项目。

## 当前支持范围

- 仅支持 iOS 工程的 Codex / Claude 配置。
- 已提供安装与回退能力（事务状态记录 + 回退脚本）。
- `codex-ios` 下发：`AGENTS.md`、`.codex/config.toml`、`.agents/skills/super-dev/**`。
- `claude-ios` 下发：`CLAUDE.md`、`.claude/settings.json`、`.mcp.json`、`.claude/skills/**`。

## 10 分钟上手（小白路径）

### 前置条件

1. 已安装 `python3`、`git`。
2. 目标项目是一个可写目录（建议先用测试仓库）。
3. 若你用 AI 助手执行命令，确保它能访问目标项目目录。

### 路径 A：让 AI 一键安装（公开仓库）

在目标项目里直接给 AI 这句提示词：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project
```

Claude 版本：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project
```

### 路径 B：本地命令安装（最稳）

```bash
python3 /path/to/super-dev/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/super-dev" \
  --profile codex-ios \
  --namespace super-dev
```

Claude：

```bash
python3 /path/to/super-dev/common/install/scripts/portable_apply.py \
  --project-root "$(pwd)" \
  --template-root "/path/to/super-dev" \
  --profile claude-ios \
  --namespace super-dev
```

### 成功标志

安装成功应输出 JSON，至少包含：

1. `status=ok`
2. `txn_id`
3. `state_file`
   - `codex-ios`: `.codex/portable/state.json`
   - `claude-ios`: `.claude/portable/state.json`

## fork 后如何自定义能力（核心）

你的目标是：在自己的 fork 中“加能力”，再安装到任意项目。

### 第 1 步：用内置 skill 把自然语言需求转成模板变更

入口（仓库内置，不下发给用户项目）：

```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "<你的需求>" \
  --pretty
```

先预览不写文件：

```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "<你的需求>" \
  --dry-run \
  --pretty
```

示例：

1. Hook（预提交本地化校验）
```text
增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验
```
2. MCP（自定义 server）
```text
增加一个 MCP server: lint-server command: uvx args: lint-mcp --stdio
```
3. 平台定向（仅 codex / 仅 claude）
```text
增加一个 MCP server: lint-server command: uvx args: lint-mcp --stdio 仅 codex
```

### 第 2 步：把 fork 模板安装到目标项目

在目标项目执行 `portable_apply.py`，`--template-root` 指向你的 fork 目录即可。

## 更新流程（安装即更新）

当你的 fork 模板发生变化后，在目标项目再次执行同一 profile 的安装命令即可更新：

- `codex-ios` 再执行一次 `portable_apply.py`
- `claude-ios` 再执行一次 `portable_apply.py`

每次更新都会生成新 `txn_id` 并写入对应 `state_file`。

## 回退

AI 一键回退提示词：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md and rollback latest transaction
```

本地命令：

```bash
python3 /path/to/super-dev/common/install/scripts/portable_rollback.py \
  --project-root "$(pwd)"
```

## 指令识别范围（platform-feature-dispatcher）

当前 `platform-feature-dispatcher` 是规则驱动识别，不是任意自然语言理解。

可稳定识别：

1. 包含 `hook`：归类为 `feature_type=hook`
2. 包含 `mcp`：归类为 `feature_type=mcp`
3. 包含 `skill`：归类为 `feature_type=skill`（提取 skill 名）
4. 其他文本：归类为 `feature_type=instruction`

当前不支持：

1. 删除语义（`删除/移除/remove/delete`）自动分发
2. 复杂多条件自然语言（同句混合多平台差异策略）
3. 超出 Claude/Codex 的第三平台分发

## 能力边界

1. 分发器只负责 `自然语言 -> intent -> actions -> ios 模板`，不直接改用户项目。
2. 用户项目修改由 installer 执行（`portable_apply.py` / `portable_rollback.py`）。
3. `profile/manifest 不会下发到用户项目`，它们只是模板仓库中的安装元数据。
4. 仓库内部开发 skill 位于 `.agents/skills/platform-feature-dispatcher`，不属于对用户下发模板。

## 私有仓库与模板缓存

- 默认缓存目录由 `SUPER_DEV_HOME` 控制，默认值：`$HOME/.super-dev`。
- 模板目录：`$HOME/.super-dev/templates/super-dev`。
- 公开仓库可直接 `raw` + `git clone https`。
- 私有仓库建议先 clone 到本地模板目录，再让 AI 读取本地 `INSTALL.md`。

## 迁移说明

- 新版本模板缓存默认放在 `SUPER_DEV_HOME`（默认 `$HOME/.super-dev`）下。
- 模板目录：`$HOME/.super-dev/templates/super-dev`。
- 历史遗留目录 `.codex/portable/template/super-dev` 可手动删除，避免被误提交。
- 项目内事务目录按 profile 保留：
  - `codex-ios`：`.codex/portable/state|backups|history|conflicts`
  - `claude-ios`：`.claude/portable/state|backups|history|conflicts`

## 验证

分层验证（契约 + golden + installer e2e）：

```bash
bash scripts/verification/run_all.sh
```

skill 黑盒验收：

```bash
python3 scripts/verification/run_skill_blackbox.py \
  --repo-root . \
  --cases tests/verification/skill_blackbox_cases.json \
  --pretty
```

真实 Agent CLI 黑盒（需本机已安装并登录 codex/claude）：

```bash
bash scripts/verification/run_agent_cli_blackbox.sh \
  --repo-root . \
  --pretty
```

## 常见问题（FAQ）

1. Claude 安装成功但文件写到了错误目录？
   - 原因：`claude -p` 以当前工作目录为项目根。
   - 解决：先 `cd` 到目标项目目录再执行 Claude 命令。
2. Codex 参数不生效？
   - 解决：优先使用 `codex exec --help` 的参数格式（推荐 `-C <project>` + `--add-dir <template-root>`）。
3. 为什么某些配置没有覆盖旧值？
   - 这是设计行为：installer 采用“补缺合并（merge missing keys）”，默认保留用户已有配置。

## 仓库结构

- `common/install/`: 通用安装入口、profile/manifest、安装与回退脚本。
- `common/platforms/`: capability matrix、intent schema 与样例。
- `ios/codex/`: iOS Codex 配置模板。
- `ios/claude/`: iOS Claude 配置模板。
- `ios/skills/`: iOS 相关 skills 模板（用于 Codex `.agents/skills/super-dev/**` 与 Claude `.claude/skills/**` 下发）。
- `tests/`: 安装/回退与文档约束测试。

## 贡献说明

欢迎 issue / PR，但该仓库目前优先服务作者自用流程，外部需求不保证及时支持。详见 `CONTRIBUTING.md`。

## 安全反馈

请勿在公开 issue 中提交敏感信息。详见 `SECURITY.md`。
