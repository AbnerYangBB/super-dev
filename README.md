# super-dev

`super-dev` 现在是一个极简的同步仓库。

它做两件事：

- 把仓库里的 `skills/` 全量同步到目标工作区的 `.agents/skills/super-dev/`
- 把仓库 `agent/` 目录内的文件同步到目标工作区根目录（不创建 `agent/` 目录本身）

## 仓库边界

本仓库会：

- 维护可复用的 `skills/`
- 维护可复用的 `agent/` 模板内容
- 提供一个同步脚本 `scripts/sync_skills.py`
- 通过一次同步完成安装或更新

本仓库不会：

- 区分 `Codex`、`Claude`、`Cursor`、`Trae`
- 区分 `iOS`、`web` 或其他 profile
- 提供安装事务、回滚或自然语言分发器

## 目标路径

仓库内：

```text
skills/ios/swift/swiftui-patterns/SKILL.md
```

同步后会分别落到目标工作区：

```text
.agents/skills/super-dev/ios/swift/swiftui-patterns/SKILL.md
```

```text
AGENTS.md
docs/test/README.md
...
```

目录层级保持原样：

- `skills/` 整体挂到 `.agents/skills/super-dev/` 下
- `agent/` 的子内容直接展开到工作区根目录（不会出现 `root/agent/...`）

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
- 同步 `agent/` 时，如果目标位置存在同名文件/目录，会先重命名原文件/目录为 `*-bak`（文件会保持原后缀，例如 `AGENTS-bak.md`），再写入新文件

## 输出格式

脚本会输出 JSON 摘要，至少包含：

- `status`
- `workspace_root`
- `dry_run`
- `skills_sync`（含 `source_root`、`target_root`、`copied`、`deleted`）
- `agent_sync`（含 `source_root`、`target_root`、`copied`、`backed_up`）

## 安全约束

同步脚本只允许：

- 读取本仓库中的 `skills/` 和 `agent/`
- 写入目标工作区中的 `.agents/skills/super-dev/`
- 写入目标工作区根目录（仅用于 `agent/` 同步对应路径）

如果你发现它会覆盖其他目录、穿透符号链接，或会影响业务代码，请不要继续执行，先提 issue 或私下反馈。

## 常见问题

### 为什么不再区分平台？

因为这个仓库现在只负责同步 `skills/` 与 `agent/` 模板，不再负责任何平台配置分发。

### 为什么没有回滚？

因为本仓库不再维护安装事务系统。它只做目录同步。

### 会不会动到我已有的其他 skills？

不会。脚本只会处理 `.agents/skills/super-dev/` 这一棵目录。

### 会不会覆盖我根目录已有的同名文件？

会先重命名旧文件或目录为 `*-bak`（若重名会自动编号，如 `*-bak-2`），然后再写入 `agent/` 的新内容。
