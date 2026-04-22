# 测试体系说明

本目录用于沉淀测试方法、模板与阶段经验。`AGENTS.md` 负责执行规则；`docs/Tests/` 负责说明边界、提供模板、沉淀案例。

## 三类测试

| 类型 | 解决什么问题 |
| --- | --- |
| `Unit Test` | 稳定业务规则、状态流转、异常路径、高回归风险点；可做确定性断言。 |
| `UI Test` | 可脚本化、可重复的用户交互主链路；如点击、跳转、静态文案、页面状态。 |
| `AI 长逻辑测试` | 仅用于复杂长流程、动态或偶发问题、或需要 AI 现场判断与排障的场景。英文别名：`Agentic Long-Flow Test`。 |

## 选择顺序

1. 先判断 `Unit Test` 能否覆盖。
2. 再判断 `UI Test` 是否需要覆盖用户主链路。
3. 只有前两者不足时，才启用 `AI 长逻辑测试`。

`AI 长逻辑测试` 不能替代前两类测试。

## `AI 长逻辑测试`：何时启用

仅在以下场景启用：

1. 长流程，且中间状态不稳定或依赖外部环境。
2. 存在动态或偶发问题，需要 AI 现场判断与排障。
3. 需要子 agent / 浏览器 / 模拟器 / Shell 联动，固定脚本断言不足。

## `AI 长逻辑测试` 最小要求

启用前必须写清：

- 测试目标
- 前置条件
- 为什么不能只靠 `Unit Test` / `UI Test`
- 执行边界与职责分工
- 成功标准与证据
- 遇到的问题与处理

模板见 [`templates/ai-long-flow-test-template.md`](templates/ai-long-flow-test-template.md)。

## Phase 沉淀

每个 Phase 新增的测试坑点、环境要求、有效策略，应写入 `docs/Tests/phase-<n>/`。当前示例见 [`phase-2/2026-04-13-map-realtime-testing-notes.md`](phase-2/2026-04-13-map-realtime-testing-notes.md)。

## 与 `docs/llm_ctx` 的分工

- `docs/llm_ctx/decisions.md`、`pitfalls.md`：跨阶段通用决策与坑点。
- `docs/Tests/`：测试选择、执行方法、模板与阶段案例。