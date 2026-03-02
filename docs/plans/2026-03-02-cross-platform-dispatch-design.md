# 跨平台能力分发架构设计（Claude Code / Codex）

- 日期：2026-03-02
- 输入：`PRD.md`
- 依赖：`docs/research/2026-03-02-claude-codex-feature-matrix.md`

## 1. 设计目标

1. 你输入一条自然语言需求（如“提交前执行本地化校验”），系统自动生成 Claude/Codex 各自正确的下发内容。
2. 平台差异由能力矩阵驱动，而不是散落在脚本里的临时 `if/else`。
3. 保留现有安装/回滚引擎，只重构“上游生成层”。
4. 建立可证据化验证体系，覆盖脚本与 skill 的真实执行结果。

## 2. 非目标

1. 当前不扩展第三平台（仅 Claude/Codex）。
2. 不重写 `portable_apply.py` / `portable_rollback.py` 的事务核心逻辑。
3. 不引入外部依赖（优先 Python stdlib）。

## 3. 方案对比

### 方案 A：安装器内硬编码分支

- 做法：在 installer 脚本中直接写“需求类型 -> 平台路径”的 `if/else`。
- 优点：实现最快。
- 缺点：
  1. 能力差异与业务逻辑耦合，难维护。
  2. 新增能力时风险高，回归面大。
  3. 无法独立验证“分发决策正确性”。

### 方案 B：能力矩阵 + Intent Schema + 分发编译器（推荐）

- 做法：
  1. `capability matrix` 维护平台能力事实；
  2. 自然语言先归一化为 `intent`；
  3. `dispatch compiler` 把 intent 编译成平台动作；
  4. `template generator` 写回 `ios/codex` 与 `ios/claude` 模板。
- 优点：
  1. 平台差异可审计、可测试、可扩展。
  2. 易于增加验证层（契约测试、golden、黑盒）。
  3. 能清晰表达 fallback 规则（如 Codex 无 hooks 时转 instruction）。
- 缺点：
  1. 前期模型设计成本较高。
  2. 需要维护 matrix 与 intent schema。

### 方案 C：纯 LLM 动态翻译（无结构化中间层）

- 做法：每次请求都让模型直接改模板文件。
- 优点：初期开发成本最低。
- 缺点：
  1. 稳定性弱，重复请求可能产生不同结果。
  2. 难做可重复验证与回归。
  3. 很难证明“为何这样分发”。

## 4. 推荐方案与原因

采用 **方案 B**。

理由：你的目标是“提出功能 -> 自动正确下发”，且明确要求可验证、可扩展。B 方案在可维护性和可验证性上显著优于 A/C，长期成本最低。

## 5. 最终架构

### 5.1 组件

1. `common/platforms/capabilities/*.json`：平台能力矩阵。
2. `common/platforms/intents/*.json`：统一意图模型。
3. `common/install/scripts/portable_dispatch.py`：分发编译器（intent -> actions）。
4. `common/install/scripts/portable_generate_templates.py`：模板生成器（actions -> files）。
5. `.agents/skills/platform-feature-dispatcher/`：仓库内部自然语言入口 skill（不下发给用户）。
6. `tests/verification/*`：分层验证与子 agent 黑盒验收。

### 5.2 数据流

1. 用户输入自然语言需求。
2. dispatcher skill 解析为 intent。
3. dispatch compiler 根据能力矩阵生成平台动作。
4. generator 更新 `ios/codex/*` 与 `ios/claude/*`。
5. installer 按 manifest/profile 下发到用户项目。
6. verification pipeline 验证结构正确性与行为正确性。

### 5.3 决策规则（示例）

- 当 `feature_type=hook`：
  1. Claude 若 hooks=支持，写原生 hooks 配置。
  2. Codex 若 hooks=不支持，写 `AGENTS.md` instruction fallback。

## 6. 验证设计

1. 契约测试：验证 dispatch 输出是否符合矩阵规则。
2. Golden 测试：验证模板生成结果是否与期望快照一致。
3. Installer E2E：验证 apply/rollback 不破坏事务语义。
4. 子 agent 黑盒：真实执行 skill，用输入/变更证据判定通过。

## 7. 风险与缓解

1. 官方能力变更：
   - 缓解：matrix 记录 `verified_at`，定期刷新。
2. fallback 语义不一致：
   - 缓解：在 intent schema 中显式声明 fallback 目的与文本模板。
3. 生成器误改：
   - 缓解：golden 快照 + 黑盒报告双保险。

## 8. 执行结论

- 选型：**方案 B（能力矩阵 + Intent + 编译器）**。
- 落地顺序：先矩阵与 schema，再编译器与生成器，最后 skill 与验证体系。

Implementation starts only after user approval of this design.
