# super-dev

可移植的 AI 工程配置仓库，当前聚焦 iOS 开发场景。
项目本身由AI自动生成. 使用 https://github.com/obra/superpowers skills框架(建议大家也安装).

## 状态声明

- 目前仅用于自用。
- 可能存在风险（包含但不限于：提示词行为偏差、安装流程变更、与目标项目配置冲突）。
- 使用前请先在测试项目验证，再应用到正式项目。

## 当前支持范围

- 仅支持 iOS 工程的 Codex / Claude 配置。
- 已提供安装与回退能力（事务状态记录 + 回退脚本）。
- `codex-ios` 下发：`AGENTS.md`、`.codex/config.toml`、`.agents/skills/super-dev/**`。
- `claude-ios` 下发：`CLAUDE.md`、`.claude/settings.json`、`.mcp.json`、`.claude/skills/**`。

## 能力分发生成（新增）

当你希望把“一个需求”自动转换为 Claude/Codex 的差异化配置时，先准备 intent，再运行生成器：

```bash
python3 common/install/scripts/portable_generate_templates.py \
  --repo-root . \
  --intent-file common/platforms/intents/examples/pre-commit-sync-loc.json \
  --pretty
```

仅查看将发生的变更（不写文件）：

```bash
python3 common/install/scripts/portable_generate_templates.py \
  --repo-root . \
  --intent-file common/platforms/intents/examples/pre-commit-sync-loc.json \
  --dry-run \
  --pretty
```

## 指令识别范围

当前 `platform-feature-dispatcher`（仓库内部 skill）是规则驱动识别，不是任意自然语言理解。入口：

```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "<你的需求>" \
  --pretty
```

可稳定识别（已覆盖黑盒用例）：

1. 包含 `hook`：归类为 `feature_type=hook`  
例：`增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验`
2. 包含 `mcp`：归类为 `feature_type=mcp`  
例：`增加一个 MCP server: example-server`
3. 包含 `skill`：归类为 `feature_type=skill`（会提取 skill 名）  
例：`增加一个 skill: sync-add-ios-loc`
4. 其他文本：归类为 `feature_type=instruction`

当前不支持（会被当作普通 instruction 或需要手工改 intent）：

1. “减少/删除/移除一个 hook” 这类删除语义（当前生成器只做增量，不做自动删除）
2. 复杂多条件自然语言（例如同一句里混合多个平台差异策略）
3. 超出 Claude/Codex 的第三平台分发

## 能力边界

1. 分发器只负责 `自然语言 -> intent -> actions -> ios 模板`，不直接改用户项目。  
2. 用户项目修改由 installer 执行（`portable_apply.py` / `portable_rollback.py`）。  
3. `profile/manifest 不会下发到用户项目`，它们只是模板仓库中的安装元数据。  
4. 仓库内部开发 skill 位于 `.agents/skills/platform-feature-dispatcher`，不属于对用户下发模板。

## 快速安装（按 AI 工具）

### Codex
给 AI 的提示词：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project
```

### Claude Code
给 AI 的提示词：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project
```

## 迁移说明

- 新版本模板缓存默认放在 `SUPER_DEV_HOME`（默认 `$HOME/.super-dev`）下。
- 模板目录：`$HOME/.super-dev/templates/super-dev`。
- 历史遗留目录 `.codex/portable/template/super-dev` 可手动删除，避免被误提交。
- 项目内事务目录按 profile 保留：
  - `codex-ios`：`.codex/portable/state|backups|history|conflicts`
  - `claude-ios`：`.claude/portable/state|backups|history|conflicts`

## 回退

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md and rollback latest transaction
```

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

## 仓库结构

- `common/install/`: 通用安装入口、profile/manifest、安装与回退脚本。
- `ios/codex/`: iOS Codex 配置模板。
- `ios/claude/`: iOS Claude 配置模板。
- `ios/skills/`: iOS 相关 skills 模板（用于 Codex `.agents/skills/super-dev/**` 与 Claude `.claude/skills/**` 下发）。
- `tests/`: 安装/回退与文档约束测试。

## 贡献说明

欢迎 issue / PR，但该仓库目前优先服务作者自用流程，外部需求不保证及时支持。详见 `CONTRIBUTING.md`。

## 贡献者工作流（分发器相关）

1. 先改能力矩阵或意图样例：`common/platforms/capabilities/*`、`common/platforms/intents/*`  
2. 用内部 skill 进行 dry-run：  
`python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py --repo-root . --prompt "<需求>" --dry-run --pretty`
3. 执行模板生成：  
`python3 common/install/scripts/portable_generate_templates.py --repo-root . --intent-file <intent.json> --pretty`
4. 跑验证：  
`bash scripts/verification/run_all.sh`  
`python3 scripts/verification/run_skill_blackbox.py --repo-root . --cases tests/verification/skill_blackbox_cases.json --pretty`

## 安全反馈

请勿在公开 issue 中提交敏感信息。详见 `SECURITY.md`。
