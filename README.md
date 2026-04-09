# super-dev

`super-dev` 现在是一个极简的 skills 仓库。

它只做一件事：把仓库里的 `skills/` 全量同步到目标工作区的 `.agents/skills/super-dev/`。

## 仓库边界

本仓库会：

- 维护可复用的 `skills/`
- 提供一个同步脚本 `scripts/sync_skills.py`
- 通过一次同步完成安装或更新

本仓库不会：

- 区分 `Codex`、`Claude`、`Cursor`、`Trae`
- 区分 `iOS`、`web` 或其他 profile
- 写入 `AGENTS.md`、`CLAUDE.md`、`.codex/config.toml`、`.cursor/rules/*`、`mcp.json` 等其他 AI 配置
- 提供安装事务、回滚或自然语言分发器

## 目标路径

仓库内：

```text
skills/ios/swift/swiftui-patterns/SKILL.md
```

同步后会落到目标工作区：

```text
.agents/skills/super-dev/ios/swift/swiftui-patterns/SKILL.md
```

目录层级保持原样，只是整体挂到 `.agents/skills/super-dev/` 下面。

## 快速使用

### AI 快速指令

在目标项目根目录，把下面这段话直接给 AI：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/INSTALL.md and sync super-dev skills into current project.
```

### 本地手动使用

如果你是自己手动执行，可以直接参考根目录 `INSTALL.md`，或者先 clone 仓库，再在仓库根目录运行：

```bash
python3 scripts/sync_skills.py --workspace-root "<你的目标工程目录>"
```

### 先预览再同步

```bash
python3 scripts/sync_skills.py --workspace-root "<你的目标工程目录>" --dry-run
```

## 更新方式

没有“安装”和“更新”的区别。

对同一个工作区重复执行同一条短指令，就是更新：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/INSTALL.md and sync super-dev skills into current project.
```

如果你是手动执行，则重复运行同一条命令即可：

```bash
python3 scripts/sync_skills.py --workspace-root "<你的目标工程目录>"
```

脚本会：

- 复制新增或变更的文件
- 只在 `.agents/skills/super-dev/` 内删除已过期的旧文件
- 不触碰 `.agents/skills/` 下其他命名空间

## 输出格式

脚本会输出 JSON 摘要，至少包含：

- `status`
- `workspace_root`
- `source_root`
- `target_root`
- `copied`
- `deleted`
- `dry_run`

## 安全约束

同步脚本只允许：

- 读取本仓库中的 `skills/`
- 写入目标工作区中的 `.agents/skills/super-dev/`

如果你发现它会覆盖其他目录、穿透符号链接，或会影响业务代码，请不要继续执行，先提 issue 或私下反馈。

## 常见问题

### 为什么不再区分平台？

因为这个仓库现在只负责同步 `skills/`，不再负责任何平台配置分发。

### 为什么没有回滚？

因为本仓库不再维护安装事务系统。它只同步 `skills/` 目录。

### 会不会动到我已有的其他 skills？

不会。脚本只会处理 `.agents/skills/super-dev/` 这一棵目录。
