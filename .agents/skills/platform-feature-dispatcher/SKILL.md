---
name: platform-feature-dispatcher
description: 将自然语言功能请求转换为 intent，并基于 capability matrix 生成 Claude/Codex 配置模板变更。
---

# Platform Feature Dispatcher

## 目标

当用户提出“增加某个 AI 能力”时，先抽象为 `intent`，再依据 `capability matrix` 自动分发到不同平台的正确配置文件。

## 输入

- 一条自然语言需求（示例：`增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验`）

## 输出

- 归一化 intent JSON
- 每个平台的 actions 决策
- 模板变更结果（由 `portable_generate_templates.py` 落盘）

## Flow

1. 解析用户需求，提取 `feature_type` / `trigger` / `tool_ref` / `platform_targets`。
2. 按 `assets/intent-template.json` 生成 intent。
3. 读取 capability matrix（`common/platforms/capabilities/*.json`）。
4. 运行分发编译：`portable_dispatch.py`（intent -> platform actions）。
5. 运行模板生成：`portable_generate_templates.py`（actions -> `ios/codex/*` 和 `ios/claude/*`）。
6. 输出变更摘要与验证命令。

## 执行命令

```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验" \
  --pretty
```

仅预览，不写文件：

```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验" \
  --dry-run \
  --pretty
```
