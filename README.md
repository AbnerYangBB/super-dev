# super-dev

可移植的 AI 工程配置仓库，当前支持 iOS 与 web 开发场景。
项目本身由 AI 自动生成，使用 https://github.com/obra/superpowers skills 框架（建议安装）。

## 状态声明

- 目前仅用于自用。
- 可能存在风险（包含但不限于：提示词行为偏差、安装流程变更、与目标项目配置冲突）。
- 使用前请先在测试项目验证，再应用到正式项目。

## 当前支持范围

- 历史基线：仅支持 iOS 工程的 Codex / Claude / Trae 配置。
- 支持 Codex / Claude / Trae 的 iOS 与 web 配置。
- iOS profiles：`codex-ios`、`claude-ios`、`trae-ios`。
- web profiles：`codex-web`、`claude-web`、`trae-web`。
- 支持安装、更新、回滚，以及通过分发器把自然语言请求写入 `ios/...` 或 `web/...` 模板。
- 共装策略：
  - iOS 与 web 可安装到同一目标项目。
  - 共享文件继续采用受管区块追加与缺失 key 合并，不覆盖用户已有配置。
  - 回退默认回退“最近一次事务”，例如最后装的是 `codex-web`，则只回退 web 这一笔。

## 开箱即用

把下面提示词直接贴给 AI（在你的目标项目目录执行）。

### 安装 Codex iOS

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project
```

### 安装 Claude iOS

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project
```

### 安装 Trae iOS

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile trae-ios in current project
```

### 安装 Codex web

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-web in current project
```

### 安装 Claude web

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-web in current project
```

### 安装 Trae web

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile trae-web in current project
```

### 更新（重复安装即可）

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-ios in current project as update
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-ios in current project as update
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile trae-ios in current project as update
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile codex-web in current project as update
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile claude-web in current project as update
```

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md and install profile trae-web in current project as update
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
In this fork repository, use .agents/skills/platform-feature-dispatcher to customize feature request: "<你的需求>" for codex, claude and trae. Run dry-run first, then apply template changes, and summarize changed files.
```

示例需求：

```text
增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验
```

```text
增加一个 MCP server: lint-server command: uvx args: lint-mcp --stdio 仅 codex
```

```text
增加一条 web instruction: 使用 frontend-design 处理页面设计
```

### 3) 在目标项目重新更新

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile codex-ios in current project using template root /path/to/your-fork. Do not clone remote repository.
```

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile claude-ios in current project using template root /path/to/your-fork. Do not clone remote repository.
```

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile trae-ios in current project using template root /path/to/your-fork. Do not clone remote repository.
```

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile codex-web in current project using template root /path/to/your-fork. Do not clone remote repository.
```

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile claude-web in current project using template root /path/to/your-fork. Do not clone remote repository.
```

```text
Read and follow instructions from /path/to/your-fork/common/install/INSTALL.md and install profile trae-web in current project using template root /path/to/your-fork. Do not clone remote repository.
```

## 常见问题

1. 我是初级开发，真的不看脚本也能用吗？
- 可以。按上面的 AI 提示词直接执行即可。

2. 更新为什么也是安装提示词？
- 这是设计行为：同一个 profile 再执行一次安装就是更新。

3. Claude 执行后文件写错目录怎么办？
- 让 AI 在“目标项目目录”执行，不要在模板仓库目录执行。

4. Codex 提示 “Not inside a trusted directory” 怎么办？
- 在 Codex 命令里增加 `--skip-git-repo-check`，或先在受信任仓库目录执行。

5. 提示词执行失败怎么办？
- 先让 AI 输出错误日志，再把日志贴回 issue 或本地排查。

6. iOS 和 web 可以一起装吗？
- 可以。建议按需要分别执行 `*-ios` 和 `*-web` profile；若要回退其中一个，注意回退默认只撤销最近一次安装事务。
