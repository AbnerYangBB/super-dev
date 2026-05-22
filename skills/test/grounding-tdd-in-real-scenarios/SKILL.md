---
name: grounding-tdd-in-real-scenarios
description: Use when you is about to enter a TDD workflow and must first clarify the user's real goal, then add real-scenario test cases around the final observable outcome. Trigger when tests for a user-visible workflow, cross-system action, or multi-step effect might otherwise stop at mock calls, API success, or partial assertions instead of what the user actually needs to see happen in the real target.
---

# Grounding TDD In Real Scenarios

## Overview

这是对 `test-driven-development` 的补强，不替代它。
它经常作为别的 workflow / testing skill 的增强层使用，把成功标准钉在“最终真实可观察结果”上。

核心原则：**流程只有在最终用户可观察结果成立时才算成功。**  
`service` 返回成功、接口被调用、mock 收到参数，都只是中间信号。

**REQUIRED BACKGROUND:** You MUST understand `test-driven-development`.

## When to Use

- 需求跨越多个步骤或系统：`翻译 -> 发送`、`转写 -> 改写 -> 插入`
- 成功标准落在文本框、文件、数据库、通知、第三方 App、消息发送等外部可观察状态
- 你发现自己想用 `called once`、`returned success`、`contains expected text` 就结束测试设计
- 需求存在真实上下文：已有内容、选区、焦点变化、并发、取消、重试、部分成功

不要用于：

- 纯函数
- 没有外部可观察副作用的单步 deterministic 逻辑

## Output Contract

在写测试前，必须先输出给人类伴侣看的两个 section：

1. `真实场景确认`
2. `补充到 TDD 的真实场景用例`

如果这两个 section 还写不清楚，先不要写测试代码。

## Bundled Resource

- `references/real-scenario-template.md`
  在需要起草 `真实场景确认` 和 `补充到 TDD 的真实场景用例` 时再打开并复用，不必整段抄入最终回复。

## Implementation

### 1. 先写 `真实场景确认`

用 `references/real-scenario-template.md`，至少写清：

- 用户最终想完成什么
- 完成后外界能直接观察到什么
- 哪些结果必须“完全一致”，不能只看“包含/不报错/有返回”
- 哪些内部信号最容易被误判成成功
- 你准备怎么读取最终状态

### 2. 明确区分两类断言

| 类型 | 作用 |
|------|------|
| `内部成功信号` | 证明链路走到了某一步 |
| `最终完成态` | 证明用户真的完成了任务 |

规则：**内部成功信号可以保留，但绝不能替代最终完成态。**

### 3. 把真实场景补进 TDD，而不是替换 TDD

标准 TDD 仍然保持最小 RED：

- 先挑一个真实场景写成 failing test
- 写最小实现让它通过
- 再从 `补充到 TDD 的真实场景用例` 里选下一个未覆盖场景继续 RED

**不要说：**“复杂场景以后补 integration。”  
正确做法是：现在就把复杂场景写进 backlog，只是按 TDD 节奏逐个落地。

### 4. 复杂场景至少补 3 类中的 1 类

- `正常路径的最终态精确断言`
- `已有环境/上下文扰动`
- `伪成功或部分成功`

常见维度：

- 目标已有内容或选区
- 接口返回成功但目标载体未变化
- 重试、取消、重复触发导致重复插入
- 焦点切换、目标失效、上下文串线

## Quick Reference

| 假成功断言 | 应补成什么 |
|-----------|------------|
| `translate() 被调用 1 次` | 目标文本框最终内容精确等于预期文本 |
| `send() 返回 success` | 读取目标载体，确认内容真的变化 |
| `contains expected text` | 确认没有重复、截断、额外前后缀 |
| `mock receiver 收到 payload` | 确认发到正确对象、正确位置、正确时机 |
| `没有抛错` | 确认用户看到的是完成态，而不是 no-op |

## Example

需求：`执行一轮翻译并发送到文本框`

`真实场景确认`

- 用户最终想要的是：当前文本被翻译一次，并准确落到目标文本框里
- 真正完成的标志是：目标文本框最终内容与预期发送文本完全一致
- 不能误判为完成的信号：
  - 翻译接口返回了文本
  - 发送接口返回 success
  - mock 文本发送器收到参数
  - 文本框里“包含了”目标片段
- 最终状态读取方式：读取目标文本框插入后的真实内容，而不是只看发送函数返回值

`补充到 TDD 的真实场景用例`

- 正常路径：文本框最终内容精确等于翻译结果
- 已有内容：替换选区后，前后文不被破坏
- 伪成功：发送函数返回成功，但文本框内容未变化，应视为失败
- 稳定性：重试、取消或重复触发时不应重复插入

## Common Mistakes

| 误区 | 修正 |
|------|------|
| “接口成功就算做完了” | 接口成功只是链路信号，不是用户完成态 |
| “mock 都对了，真实载体以后再测” | 这会把关键成功标准从本轮测试设计中删掉 |
| “包含目标文本就够了” | 可能仍有重复、截断、顺序错误或脏前后缀 |
| “复杂场景以后补” | 现在就写进 TDD backlog，再按 RED 节奏逐个落地 |

## Red Flags

- “调用成功就算完成”
- “真实目标太贵，先不测”
- “只要 mock 对就够了”
- “包含目标文本就够了”
- “复杂场景等实现稳定再补”

出现这些话时，先重写 `真实场景确认`，再继续。
