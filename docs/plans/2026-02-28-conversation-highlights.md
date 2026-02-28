# 2026-02-28 会话精华（恢复上下文）

## 1. 项目定位

- 仓库目标：构建可移植的 AI 工程配置。
- 当前范围：仅支持 iOS 开发场景下的 Codex 模板。
- 分发策略：单仓库模板，后续可扩展到 Claude / Web。

## 2. 核心约束（已定）

- 安装过程只允许修改 AI 配置文件，不改业务代码。
- 默认不覆盖用户现有配置，采用增量策略。
- skills 安装到命名空间目录：`.agents/skills/super-dev/`。
- 必须支持一键应用与一键回退。

## 3. 已实现能力

- 安装/回退引擎：
  - `common/install/scripts/portable_apply.py`
  - `common/install/scripts/portable_rollback.py`
  - `common/install/scripts/portable_config.py`
- 元数据驱动：`profile + manifest`（`codex-ios`）。
- 事务状态：项目内 `.codex/portable/state|backups|history|conflicts`。

## 4. 关键变更（最近）

- 模板缓存从项目内迁移到 HOME：
  - `SUPER_DEV_HOME`（默认 `$HOME/.super-dev`）
  - 模板目录：`$HOME/.super-dev/templates/super-dev`
- 目的：避免 `.codex/portable/template/*` 污染用户仓库提交。
- 兼容：公开仓库可用 raw 指令；私有场景走本地模板读取 fallback。

## 5. 当前可用入口

- 安装（公开仓库）：
  - `Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md`
- 回退（公开仓库）：
  - `Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md`

## 6. 风险声明

- 仓库当前以自用为主。
- 已在 README 明确：目前仅用于自用，可能存在风险，建议先在测试项目验证。

## 7. 下次继续建议起点

1. 新增 `claude-ios` profile/manifest（复用现有安装引擎）。
2. 新增 `codex-web` profile/manifest（验证跨平台路径映射）。
3. 增加安装版本锁定与升级策略（tag/version pin）。
