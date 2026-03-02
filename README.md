# super-dev

可移植的 AI 工程配置仓库，当前聚焦 iOS 开发场景。
项目本身由 AI 自动生成，使用 https://github.com/obra/superpowers skills 框架（建议安装）。

## 状态声明

- 目前仅用于自用。
- 可能存在风险（包含但不限于：提示词行为偏差、安装流程变更、与目标项目配置冲突）。
- 使用前请先在测试项目验证，再应用到正式项目。

## 当前支持范围

- 仅支持 iOS 工程的 Codex / Claude 配置。
- `codex-ios` 下发：`AGENTS.md`、`.codex/config.toml`、`.agents/skills/super-dev/**`。
- `claude-ios` 下发：`CLAUDE.md`、`.claude/settings.json`、`.mcp.json`、`.claude/skills/**`。
- 支持安装、更新、回滚。

## 开箱即用

把下面提示词直接贴给 AI（在你的目标项目目录执行）。

### 安装 Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project
```

### 安装 Claude

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project
```

### 更新（重复安装即可）

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project as update
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project as update
```

## 卸载

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md and rollback latest transaction
```

## 功能定制

目标：你在自己的 fork 里定制能力，然后让 AI 把新能力重新更新到目标项目。

### 1) 先 fork 本仓库

在 GitHub 上 fork 一份你自己的仓库。

### 2) 在 fork 里让 AI 定制能力

```text
In this fork repository, use .agents/skills/platform-feature-dispatcher to customize feature request: "<你的需求>" for codex and claude. Run dry-run first, then apply template changes, and summarize changed files.
```

示例需求：

```text
增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验
```

```text
增加一个 MCP server: lint-server command: uvx args: lint-mcp --stdio 仅 codex
```

### 3) 在目标项目重新更新

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile codex-ios in current project using template root /path/to/your-fork. Do not clone remote repository.
```

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile claude-ios in current project using template root /path/to/your-fork. Do not clone remote repository.
```

## 常见问题

1. 我是初级开发，真的不看脚本也能用吗？
- 可以。按上面的 AI 提示词直接执行即可。

2. 更新为什么也是安装提示词？
- 这是设计行为：同一个 profile 再执行一次安装就是更新。

3. Claude 执行后文件写错目录怎么办？
- 让 AI 在“目标项目目录”执行，不要在模板仓库目录执行。

4. 提示词执行失败怎么办？
- 先让 AI 输出错误日志，再把日志贴回 issue 或本地排查。
