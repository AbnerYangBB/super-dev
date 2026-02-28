# super-dev

可移植的 AI 工程配置仓库，当前聚焦 iOS 开发场景。

## 状态声明

- 目前仅用于自用。
- 可能存在风险（包含但不限于：提示词行为偏差、安装流程变更、与目标项目配置冲突）。
- 使用前请先在测试项目验证，再应用到正式项目。

## 当前支持范围

- 仅支持 iOS 工程的 Codex 配置。
- 已提供安装与回退能力（事务状态记录 + 回退脚本）。

## 快速安装（公开仓库场景）

给 AI 的提示词：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/INSTALL.md
```

## 私有仓库回退方案

当 `raw.githubusercontent.com` 无法访问（例如私有仓库）时，先拉取模板再让 AI 读取本地安装文档：

```bash
git clone --depth=1 git@github.com:AbnerYangBB/super-dev.git .codex/portable/template/super-dev
```

```text
Read and follow instructions from .codex/portable/template/super-dev/common/install/INSTALL.md
```

## 回退

```text
Fetch and follow instructions from https://raw.githubusercontent.com/AbnerYangBB/super-dev/main/common/install/ROLLBACK.md
```

## 仓库结构

- `common/install/`: 通用安装入口、profile/manifest、安装与回退脚本。
- `ios/codex/`: iOS Codex 配置模板。
- `ios/skills/`: iOS 相关 skills 模板。
- `tests/`: 安装/回退与文档约束测试。

## 贡献说明

欢迎 issue / PR，但该仓库目前优先服务作者自用流程，外部需求不保证及时支持。详见 `CONTRIBUTING.md`。

## 安全反馈

请勿在公开 issue 中提交敏感信息。详见 `SECURITY.md`。
