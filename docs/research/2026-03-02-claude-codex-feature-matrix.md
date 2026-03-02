# Claude Code / Codex 官方能力矩阵（2026-03-02）

## 目标

基于官方文档建立可执行的能力差异矩阵，作为“统一需求 -> 平台下发动作”分发器的唯一事实来源（Single Source of Truth）。

## 调研范围

- 平台：Claude Code、Codex CLI
- 能力类型：上下文记忆、Hooks、Skills、命令扩展、Subagents、MCP、安全策略、配置路径
- 时间：`2026-03-02`（UTC）

## 能力矩阵（官方来源）

| capability_id | 能力 | 给 AI 增强的能力 | Claude Code（官方） | Codex CLI（官方） | 分发策略 |
|---|---|---|---|---|---|
| context_memory | 项目上下文记忆文件 | 让模型长期遵循团队规则、项目约束、流程约定 | 支持；支持多级 `CLAUDE.md`（企业/用户/项目/子目录） | 支持；支持多级 `AGENTS.md`（global/root/subdir） | 原生直写对应记忆文件 |
| hooks | 钩子事件机制 | 在关键时机执行自动校验/阻断/提示 | 支持；`settings` 中 `hooks`，事件包括 `PreToolUse` / `PostToolUse` / `Notification` / `Stop` / `SubagentStop` | 官方文档未提供 hooks 配置能力（截至本次调研） | Claude 走原生 hook；Codex 走 instruction fallback（写入 `AGENTS.md`） |
| skills | 技能包目录 | 让 AI 可按主题复用结构化能力（步骤、脚本、约束） | 支持；项目级 `.claude/skills`，用户级 `~/.claude/skills` | 支持；用户级 `~/.codex/skills`，项目级 `./codex/skills` | 原生路径下发；必要时附加记忆文件指引 |
| command_ext | 命令扩展机制 | 让 AI 快速触发标准动作模板 | 支持 `/` 命令，支持项目级 `.claude/commands` 与用户级 `~/.claude/commands` | 支持交互命令（`/help` 列出），支持 prompt 前缀（`prompt.md`） | Claude 用 commands；Codex 用 prompt 前缀或记忆指令 |
| subagents | 子代理机制 | 让复杂任务拆分并行，降低主代理上下文压力 | 支持；项目级 `.claude/agents` 与用户级 `~/.claude/agents` | 官方文档未见等价“子代理配置文件”能力（截至本次调研） | Claude 原生；Codex 走流程指令 fallback |
| mcp | MCP 服务器接入 | 给 AI 提供外部工具/知识通道 | 支持；可通过命令添加，也可通过本地配置文件（如 `.mcp.json`）管理 | 支持；`~/.codex/config.toml` 的 `[mcp_servers.<name>]` 配置 | 双平台原生下发各自配置文件 |
| security | 权限/沙箱/审批 | 控制高风险操作，提升可控性 | 支持 settings 权限与 hooks 审计链路 | 支持 `sandbox_mode`、`approval_policy` 等配置 | 映射到各自原生安全配置键 |
| config_locations | 配置位置优先级 | 保证生成内容写入正确目录，避免“写了但不生效” | 支持多级配置：enterprise / user / project / local | 核心配置在 `~/.codex/config.toml`，指令上下文在 `AGENTS.md` | 分发器必须显式携带目标路径与优先级 |

## 关键差异结论（用于分发器决策）

1. **Hooks 与 Subagents 不对等**：Claude 有原生机制，Codex 官方文档未给出等价配置，需 fallback。
2. **Skills 目录不对等**：Claude 使用 `.claude/skills`，Codex 使用 `./codex/skills`（项目级）或 `~/.codex/skills`（用户级）。
3. **命令扩展能力形态不同**：Claude 可落地 commands 文件；Codex 更偏交互命令 + prompt 前缀。
4. **MCP 双平台均可原生支持**：但配置文件结构不同，分发器应做结构化映射而非文本拼接。

## 官方来源（Primary Sources）

### Claude Code（Anthropic）

- Settings（含配置文件路径与 hooks 配置）：
  - https://docs.anthropic.com/en/docs/claude-code/settings
- Hooks（事件类型与 matcher 机制）：
  - https://docs.anthropic.com/en/docs/claude-code/hooks
- Memory（`CLAUDE.md` 层级与导入）：
  - https://docs.anthropic.com/en/docs/claude-code/memory
- Skills（`.claude/skills` / `~/.claude/skills`）：
  - https://docs.anthropic.com/en/docs/claude-code/skills
- Slash Commands（`.claude/commands`）：
  - https://docs.anthropic.com/en/docs/claude-code/slash-commands
- Subagents（`.claude/agents`）：
  - https://docs.anthropic.com/en/docs/claude-code/sub-agents
- MCP（项目配置与命令）：
  - https://docs.anthropic.com/en/docs/claude-code/mcp

### Codex CLI（OpenAI）

- Codex README（交互命令与配置总览）：
  - https://github.com/openai/codex/blob/main/README.md
- AGENTS.md 规则与 Skills 目录说明：
  - https://github.com/openai/codex/blob/main/docs/agents.md
- config.toml（`sandbox_mode` / `approval_policy` / `mcp_servers`）：
  - https://github.com/openai/codex/blob/main/docs/config.md
- Prompting（prompt 前缀能力）：
  - https://github.com/openai/codex/blob/main/docs/prompting.md

## 验证时间戳

- verified_at: `2026-03-02`
- verifier: `codex/gpt-5`
