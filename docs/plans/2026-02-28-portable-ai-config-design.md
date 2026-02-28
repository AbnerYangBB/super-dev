# 可移植 AI 工程配置设计（首版）

- 日期：2026-02-28
- 范围：仅 iOS 开发场景下的 Codex 模板（后续可扩展）
- 目标：让 AI 可通过单条自然语言入口完成安装，并支持一键回退

## 1. 目标与约束

### 1.1 目标
1. 提供可移植、可复用、可扩展的 AI 配置模板。
2. 安装入口优先面向 AI 自然语言执行（而非人工手动步骤）。
3. 支持将模板安装到任意用户项目，路径映射可配置。
4. 支持一键应用与一键回退。

### 1.2 约束
1. 仅允许修改 AI 配置文件，不修改业务代码。
2. 不直接替换用户现有配置，默认增量合并。
3. skill 安装路径使用命名空间：`.agents/skills/super-dev/`。
4. 首版分发形态为单仓库模板。

## 2. 总体架构

### 2.1 目录职责
1. `common/`：安装框架与跨平台规则（入口文档、manifest、profile、脚本）。
2. `ios/`：iOS 模板内容（`codex` 配置、iOS 相关 skills）。

### 2.2 安装落地产物（用户项目内）
1. `.codex/portable/state.json`：记录安装事务（版本、profile、文件变更、备份路径）。
2. `.codex/portable/backups/<txn-id>/`：应用前快照。
3. `.codex/portable/history/`：应用与回退历史。
4. `.codex/portable/conflicts/`：冲突输出（用户配置优先保留）。

## 3. 路径适配模型

### 3.1 解耦原则
1. `manifest` 只声明“装什么”。
2. `profile` 只声明“装到哪里”。
3. 安装引擎按 `manifest + profile` 执行，不写死平台路径。

### 3.2 codex-ios 首版映射
1. `ios/codex/AGENTS.md -> ${PROJECT_ROOT}/AGENTS.md`
2. `ios/codex/config.toml -> ${PROJECT_ROOT}/.codex/config.toml`
3. `ios/skills/** -> ${PROJECT_ROOT}/.agents/skills/super-dev/**`

## 4. 变更策略（不覆盖）

### 4.1 策略类型
1. `append_block`：向目标文件追加受管区块（带 begin/end marker）。
2. `merge_keys`：按 key 合并配置（优先保留用户已有值）。
3. `sync_additive`：只在托管目录内新增或更新，不删除用户其他目录内容。

### 4.2 冲突策略
1. 默认保留用户配置。
2. 冲突内容输出到 `.codex/portable/conflicts/`。
3. 仅 `.agents/skills/super-dev/` 视为模板托管范围。

## 5. 一键应用与一键回退

### 5.1 一键应用
入口：AI 执行远程 `INSTALL.md`。

流程：
1. 读取 `profile` 与 `manifest`。
2. 执行预检（路径、权限、模板完整性）。
3. 备份将变更文件。
4. 应用策略（append/merge/sync）。
5. 记录 `state.json` 与历史日志。
6. 任一步失败则自动回滚。

### 5.2 一键回退
入口：AI 执行远程 `ROLLBACK.md`。

流程：
1. 读取最新（或指定）事务。
2. 按备份恢复文件。
3. 删除该事务新增文件。
4. 写入回退历史。

## 6. AI 可执行入口规范

### 6.1 INSTALL.md 要求
1. 明确 `Hard Rules`：仅改 AI 配置文件、禁止业务代码改动、必须先备份。
2. 明确参数：`profile`、`namespace`、`mode`。
3. 明确可验证产物：`state.json`、变更清单、冲突清单。

### 6.2 ROLLBACK.md 要求
1. 支持 `latest` 与指定 `txn-id`。
2. 回退必须基于 `state.json` 和备份，不做猜测性恢复。
3. 输出回退报告。

## 7. 扩展策略（未来）

1. 新增 `claude-ios`：仅新增 profile/manifest。
2. 新增 `codex-web`：仅新增 profile/manifest。
3. 统一安装引擎保持不变。

## 8. 验收标准（首版）

1. AI 能按 `INSTALL.md` 将 codex-ios 模板安装到目标项目。
2. 用户已有配置不被整文件覆盖。
3. `.agents/skills/super-dev/` 正确同步 iOS skills。
4. 一键回退后恢复到安装前状态。
5. 全流程不触碰业务代码文件。
