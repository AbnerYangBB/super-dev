# Claude iOS 配置下发设计（首版）

- 日期：2026-03-01
- 范围：在现有 portable installer 中新增 `claude-ios` 配置下发能力
- 目标：复用现有事务化安装/回退引擎，为 Claude Code 提供项目级共享配置下发

## 1. 需求背景

当前仓库仅支持 `codex-ios`。下一阶段需要支持 Claude Code，并保持：
1. 仅改 AI 配置文件，不改业务代码。
2. 默认增量合并，不覆盖用户已有配置。
3. 支持一键应用与一键回退。

## 2. 官方实践调研结论（Claude Code）

基于 Anthropic 官方文档，提炼出本仓库可落地的下发实践：
1. 共享项目配置优先放在仓库级文件（`CLAUDE.md`、`.claude/settings.json`、可选 `.mcp.json`）。
2. 本地/个人配置使用 `~/.claude/settings.json` 或项目 `.claude/settings.local.json`，不应由模板强制下发。
3. `CLAUDE.md` 用于团队共享指令，项目和子目录可分层。
4. 权限建议遵循最小化原则，在 settings 中限制高风险读取/命令。

## 3. 方案对比

### 方案 A：仅下发 `CLAUDE.md`

优点：
1. 最简单、风险最低。

缺点：
1. 无法沉淀项目级权限基线，实践不完整。

### 方案 B：下发 `CLAUDE.md` + `.claude/settings.json`（推荐）

优点：
1. 覆盖官方推荐的项目级共享配置入口。
2. 可把安全基线（permissions）以非破坏方式补齐。
3. 与当前 installer 架构兼容。

缺点：
1. 需要安装引擎新增 JSON 增量合并策略。

### 方案 C：再额外下发 `.mcp.json` / `.claude/agents`

优点：
1. 能覆盖更多高级能力。

缺点：
1. 需要更多运行环境假设（MCP 命令、凭据），首版容易引入噪音。

## 4. 选型与范围

采用方案 B，首版只做：
1. `CLAUDE.md`：受管区块追加（`append_block`）。
2. `.claude/settings.json`：只补缺失 key（新策略 `merge_json_keys`）。
3. 新增 `claude-ios` profile/manifest，并在文档中公开可选 profile。

暂不做：
1. `.mcp.json` 默认下发。
2. `.claude/agents` 与命令集下发。

## 5. 关键设计

### 5.1 新增安装策略 `merge_json_keys`

1. 读取源/目标 JSON。
2. 目标文件不存在则直接创建。
3. 目标存在时递归补齐缺失 key，保留用户已有值。
4. 目标 JSON 非法时生成 conflict 记录，不覆盖原文件。

### 5.2 `claude-ios` 映射

1. `ios/claude/CLAUDE.md -> CLAUDE.md`
2. `ios/claude/settings.json -> .claude/settings.json`

### 5.3 回退行为

1. 复用现有事务记录与回退逻辑。
2. apply 中途失败继续沿用“自动回滚已写入变更”。

## 6. 验收标准

1. `portable_apply.py --profile claude-ios` 可成功安装目标文件。
2. 既有 `.claude/settings.json` 的用户 key 不被覆盖。
3. 目标 settings 非法 JSON 时输出 conflict 且不中断安装。
4. 全量测试通过。
