# 跨平台 AI 能力分发 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个“单一意图、多平台下发”的能力分发框架，把一条抽象需求自动映射为 Claude Code / Codex 的正确配置变更，并用该框架重生成现有 iOS 配置模板。

**Architecture:** 先建立基于官方文档校验的能力矩阵（platform capability matrix），再定义统一意图模型（intent schema），最后由确定性分发器把 intent 编译为平台动作（platform actions）。安装与回滚仍复用现有 `portable_apply.py` / `portable_rollback.py`，新框架只负责上游模板生成与变更编排。新增一个 dispatcher skill，把自然语言需求转成 intent 并触发模板生成。

**Tech Stack:** Python 3 标准库（`json`、`pathlib`、`argparse`、`unittest`、`subprocess`），Markdown 文档，现有 portable installer 脚本。

---

### Task 1: 官方能力矩阵与架构脑暴（硬门禁）

**Files:**
- Create: `docs/research/2026-03-02-claude-codex-feature-matrix.md`
- Create: `docs/plans/2026-03-02-cross-platform-dispatch-design.md`
- Modify: `PRD.md`

**Step 1: 先写失败测试**

```python
# tests/portable_config/test_docs.py

def test_research_doc_and_design_doc_exist(self):
    self.assertTrue((REPO_ROOT / "docs" / "research" / "2026-03-02-claude-codex-feature-matrix.md").exists())
    self.assertTrue((REPO_ROOT / "docs" / "plans" / "2026-03-02-cross-platform-dispatch-design.md").exists())
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_docs.TestInstallDocs -v`  
Expected: FAIL（新文档尚未创建）。

**Step 3: 最小实现**

- 仅使用官方来源（Anthropic / OpenAI）沉淀能力矩阵字段：`capability`、`platform`、`supported`、`config_path`、`fallback_strategy`、`source_url`、`verified_at`。
- 在设计文档提出 2-3 个架构方案并给出推荐方案与取舍。
- 明确写入门禁：`未获用户确认前，不进入实现阶段（Task 2+）`。

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_docs.TestInstallDocs -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add docs/research/2026-03-02-claude-codex-feature-matrix.md docs/plans/2026-03-02-cross-platform-dispatch-design.md PRD.md tests/portable_config/test_docs.py
git commit -m "docs: 增加能力矩阵与分发架构设计"
```

### Task 2: 建立能力矩阵数据模型

**Files:**
- Create: `common/platforms/capabilities/schema.json`
- Create: `common/platforms/capabilities/claude-code.json`
- Create: `common/platforms/capabilities/codex-cli.json`
- Create: `tests/portable_config/test_capability_matrix.py`

**Step 1: 先写失败测试**

```python
def test_capability_matrix_has_required_fields(self):
    for item in matrix["capabilities"]:
        self.assertIn("id", item)
        self.assertIn("support", item)
        self.assertIn("config_path", item)
        self.assertIn("fallback", item)
        self.assertIn("source_url", item)
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_capability_matrix -v`  
Expected: FAIL（schema / data 缺失）。

**Step 3: 最小实现**

```json
{
  "platform": "codex-cli",
  "capabilities": [
    {
      "id": "pre_command_hook",
      "support": "unsupported",
      "config_path": null,
      "fallback": "instruction_block",
      "source_url": "https://platform.openai.com/docs/...",
      "verified_at": "2026-03-02"
    }
  ]
}
```

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_capability_matrix -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add common/platforms/capabilities tests/portable_config/test_capability_matrix.py
git commit -m "feat: 增加平台能力矩阵模型"
```

### Task 3: 定义统一意图规范（Intent Schema）

**Files:**
- Create: `common/platforms/intents/schema.json`
- Create: `common/platforms/intents/examples/pre-commit-sync-loc.json`
- Create: `tests/portable_config/test_intent_schema.py`

**Step 1: 先写失败测试**

```python
def test_pre_commit_intent_example_is_valid(self):
    intent = load_json("common/platforms/intents/examples/pre-commit-sync-loc.json")
    self.assertEqual(intent["feature_type"], "hook")
    self.assertEqual(intent["trigger"], "pre_commit")
    self.assertIn("sync-add-ios-loc", intent["tool_ref"])
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_intent_schema -v`  
Expected: FAIL（intent 文件不存在）。

**Step 3: 最小实现**

```json
{
  "id": "ios_loc_pre_commit_check",
  "feature_type": "hook",
  "trigger": "pre_commit",
  "tool_ref": "skill:sync-add-ios-loc",
  "desired_behavior": "validate localization before commit",
  "platform_targets": ["claude-code", "codex-cli"]
}
```

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_intent_schema -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add common/platforms/intents tests/portable_config/test_intent_schema.py
git commit -m "feat: 增加 intent 规范与示例"
```

### Task 4: 实现分发编译器（Intent -> Platform Actions）

**Files:**
- Create: `common/install/scripts/portable_dispatch.py`
- Create: `tests/portable_config/test_portable_dispatch.py`

**Step 1: 先写失败测试**

```python
def test_dispatch_hook_intent_outputs_platform_specific_actions(self):
    result = dispatch_intent(intent)
    self.assertEqual(result["claude-code"][0]["operation"], "merge_json_keys")
    self.assertEqual(result["codex-cli"][0]["operation"], "append_block")
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_portable_dispatch -v`  
Expected: FAIL（分发器不存在）。

**Step 3: 最小实现**

```python
def dispatch_intent(intent, capability_matrix):
    # 规则：优先平台原生能力；不支持时使用 fallback
    if capability_matrix["claude-code"]["pre_command_hook"]["support"] == "supported":
        claude_action = {"operation": "merge_json_keys", "target": ".claude/hooks.json"}
    else:
        claude_action = {"operation": "append_block", "target": "CLAUDE.md"}
    codex_action = {"operation": "append_block", "target": "AGENTS.md"}
    return {"claude-code": [claude_action], "codex-cli": [codex_action]}
```

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_portable_dispatch -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add common/install/scripts/portable_dispatch.py tests/portable_config/test_portable_dispatch.py
git commit -m "feat: 实现 intent 分发编译器"
```

### Task 5: 实现模板生成器（Platform Actions -> ios 模板）

**Files:**
- Create: `common/install/scripts/portable_generate_templates.py`
- Create: `tests/portable_config/test_template_generation.py`
- Modify: `README.md`

**Step 1: 先写失败测试**

```python
def test_generate_updates_codex_and_claude_templates(self):
    run_generate("common/platforms/intents/examples/pre-commit-sync-loc.json")
    self.assertIn("sync-add-ios-loc", (REPO_ROOT / "ios" / "codex" / "AGENTS.md").read_text())
    self.assertIn("sync-add-ios-loc", (REPO_ROOT / "ios" / "claude" / "CLAUDE.md").read_text())
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_template_generation -v`  
Expected: FAIL（生成脚本不存在）。

**Step 3: 最小实现**

```python
# common/install/scripts/portable_generate_templates.py
# 1) 读取 intent
# 2) 调用 dispatch
# 3) 依据平台动作写入 ios/codex/* 与 ios/claude/*
# 4) 输出 JSON 变更摘要
```

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_template_generation -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add common/install/scripts/portable_generate_templates.py tests/portable_config/test_template_generation.py README.md
git commit -m "feat: 增加模板生成流水线"
```

### Task 6: 将生成产物接入 Installer 元数据

**Files:**
- Modify: `common/install/manifests/codex-ios.json`
- Modify: `common/install/manifests/claude-ios.json`
- Modify: `common/install/profiles/codex-ios.json`
- Modify: `common/install/profiles/claude-ios.json`
- Modify: `tests/portable_config/test_portable_apply.py`

**Step 1: 先写失败测试**

```python
def test_apply_uses_generated_platform_targets(self):
    codex = self._run_apply(profile="codex-ios")
    claude = self._run_apply(profile="claude-ios")
    self.assertEqual(codex.returncode, 0)
    self.assertEqual(claude.returncode, 0)
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_portable_apply -v`  
Expected: FAIL（profile/manifest 与生成产物尚未对齐）。

**Step 3: 最小实现**

- manifest 指向新生成模板。
- 保持非破坏策略（`append_block` / `merge_*` / `sync_additive_dir`）不变。
- 按架构决议统一 Claude skills 路径并补兼容测试。

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_portable_apply -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add common/install/manifests common/install/profiles tests/portable_config/test_portable_apply.py
git commit -m "refactor: 对齐 installer 元数据与生成模板"
```

### Task 7: 新增 Dispatcher Skill（自然语言需求入口）

**Files:**
- Create: `.agents/skills/platform-feature-dispatcher/SKILL.md`
- Create: `.agents/skills/platform-feature-dispatcher/assets/intent-template.json`
- Create: `.agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py`
- Modify: `tests/portable_config/test_docs.py`

**Step 1: 先写失败测试**

```python
def test_dispatcher_skill_doc_contains_flow(self):
    text = (REPO_ROOT / ".agents" / "skills" / "platform-feature-dispatcher" / "SKILL.md").read_text()
    self.assertIn("intent", text)
    self.assertIn("capability matrix", text)
    self.assertIn("portable_generate_templates.py", text)
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_docs -v`  
Expected: FAIL（skill 未创建）。

**Step 3: 最小实现**

```text
Flow:
1) 解析用户需求 -> intent JSON
2) 基于 capability matrix 做平台可行性判定
3) 生成平台 patch 动作
4) 写回 ios 模板
5) 返回变更摘要与验证命令
```

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_docs -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add .agents/skills/platform-feature-dispatcher tests/portable_config/test_docs.py
git commit -m "feat: 增加平台能力分发 skill"
```

### Task 8: 依据新框架重生成现有 iOS Codex/Claude 模板

**Files:**
- Modify: `ios/codex/AGENTS.md`
- Modify: `ios/codex/config.toml`
- Modify: `ios/claude/CLAUDE.md`
- Modify: `ios/claude/settings.json`
- Modify: `ios/claude/mcp.json`
- Create or Modify: `ios/claude/hooks.json`
- Modify: `tests/portable_config/test_portable_apply.py`
- Modify: `tests/portable_config/test_portable_rollback.py`

**Step 1: 先写失败测试**

```python
def test_generated_templates_include_loc_pre_commit_behavior(self):
    self.assertIn("sync-add-ios-loc", (REPO_ROOT / "ios" / "codex" / "AGENTS.md").read_text())
    self.assertIn("sync-add-ios-loc", (REPO_ROOT / "ios" / "claude" / "CLAUDE.md").read_text())
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.portable_config.test_portable_apply tests.portable_config.test_portable_rollback -v`  
Expected: FAIL（模板尚未重生成）。

**Step 3: 最小实现**

- 执行 Task 5 的生成命令。
- 将生成结果回写并纳入版本控制。
- 不改动现有事务回滚机制。

**Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.portable_config.test_portable_apply tests.portable_config.test_portable_rollback -v`  
Expected: PASS。

**Step 5: 提交**

```bash
git add ios/codex ios/claude tests/portable_config/test_portable_apply.py tests/portable_config/test_portable_rollback.py
git commit -m "feat: 按新框架重生成 codex/claude 模板"
```

### Task 9: 建立分层验证框架（单测/集成/快照）

**Files:**
- Create: `tests/verification/test_dispatch_contract.py`
- Create: `tests/verification/test_template_golden.py`
- Create: `tests/verification/test_installer_e2e.py`
- Create: `tests/verification/fixtures/intents/pre-commit-sync-loc.json`
- Create: `tests/verification/fixtures/golden/codex_AGENTS.md`
- Create: `tests/verification/fixtures/golden/claude_CLAUDE.md`
- Create: `scripts/verification/run_all.sh`

**Step 1: 先写失败测试**

```python
def test_dispatch_contract_pre_commit_hook(self):
    result = dispatch_intent(sample_intent)
    self.assertEqual(result["codex-cli"][0]["operation"], "append_block")
    self.assertIn(result["claude-code"][0]["operation"], {"merge_json_keys", "append_block"})
```

**Step 2: 跑测试确认失败**

Run:
- `python3 -m unittest tests.verification.test_dispatch_contract -v`
- `python3 -m unittest tests.verification.test_template_golden -v`
- `python3 -m unittest tests.verification.test_installer_e2e -v`

Expected: FAIL（验证目录与夹具尚未建立）。

**Step 3: 最小实现**

- 分发契约测试：验证 `intent -> platform actions` 的关键字段与 fallback 路径。
- 模板金丝雀快照测试：生成后模板与 golden 文件做逐行比对（允许时间戳等白名单字段忽略）。
- installer 端到端测试：在临时目录执行 apply/rollback，断言事务状态和回滚清理。

**Step 4: 跑测试确认通过**

Run:
- `python3 -m unittest tests.verification.test_dispatch_contract -v`
- `python3 -m unittest tests.verification.test_template_golden -v`
- `python3 -m unittest tests.verification.test_installer_e2e -v`

Expected: PASS。

**Step 5: 提交**

```bash
git add tests/verification scripts/verification/run_all.sh
git commit -m "test: 增加分层验证框架"
```

### Task 10: 子 Agent CLI 黑盒验收（Skill 执行结果）

**Files:**
- Create: `tests/verification/skill_blackbox_cases.json`
- Create: `scripts/verification/run_skill_blackbox.py`
- Create: `docs/verification/skill-blackbox-protocol.md`
- Modify: `README.md`

**Step 1: 先写失败测试**

```python
def test_skill_blackbox_case_pre_commit_loc(self):
    report = run_blackbox_case("pre_commit_loc")
    self.assertEqual(report["status"], "passed")
    self.assertIn("ios/codex/AGENTS.md", report["changed_files"])
    self.assertTrue(any("sync-add-ios-loc" in line for line in report["evidence"]))
```

**Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.verification.test_skill_blackbox -v`  
Expected: FAIL（黑盒执行器与测试用例尚未实现）。

**Step 3: 最小实现**

- 构建黑盒协议：`输入 prompt -> 子 agent 执行 skill -> 收集文件 diff -> 断言预期证据`。
- 使用子 agent CLI（会话内 `spawn_agent/send_input/wait`）执行标准用例集：
  - 用例 A：`增加一个 Hook: 提交前使用 sync-add-ios-loc 做校验`
  - 用例 B：`增加一个 MCP server（仅 Claude 生效，Codex 转 instruction fallback）`
  - 用例 C：`增加一条通用 instruction（Claude/Codex 双端）`
- 记录每个用例输出：`input`、`expected_actions`、`actual_actions`、`changed_files`、`evidence`、`pass/fail`。

**Step 4: 跑测试确认通过**

Run:
- `python3 scripts/verification/run_skill_blackbox.py --cases tests/verification/skill_blackbox_cases.json`
- `python3 -m unittest tests.verification.test_skill_blackbox -v`

Expected: PASS；输出 `blackbox-report.json`，每个 case 有可追溯证据。

**Step 5: 提交**

```bash
git add tests/verification/skill_blackbox_cases.json scripts/verification/run_skill_blackbox.py docs/verification/skill-blackbox-protocol.md README.md
git commit -m "test: 增加 skill 子agent 黑盒验收"
```

### Task 11: 全量回归、评审与交接

**Files:**
- Modify: `docs/plans/2026-03-02-cross-platform-ai-feature-dispatch-implementation-plan.md`
- Modify: `README.md`
- Optional Modify: `docs/research/2026-03-02-claude-codex-feature-matrix.md`

**Step 1: 跑完整验证脚本**

Run:
- `bash scripts/verification/run_all.sh`
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`

Expected: 全部 PASS。

**Step 2: 请求评审**

使用 `@superpowers/requesting-code-review`，附：
- 能力矩阵文档
- dispatch 编译器
- 模板重生成 diff
- 分层验证报告
- 子 agent 黑盒报告

**Step 3: 处理评审意见**

使用 `@superpowers/receiving-code-review` 严格校验并落地修改。

**Step 4: 完成前验证**

使用 `@superpowers/verification-before-completion` 重跑全量回归。

**Step 5: 最终提交**

```bash
git add README.md docs/research docs/plans docs/verification
git commit -m "docs: 完成跨平台分发框架交接"
```

---

## 执行门禁

1. 先完成 **Task 1**，然后停止。
2. 向用户展示 `docs/plans/2026-03-02-cross-platform-dispatch-design.md` 并等待确认。
3. 用户确认后再继续 Task 2+。

## 实施规则

- 每个代码任务必须遵循 TDD：先失败测试 -> 最小实现 -> 测试通过。
- 严格 DRY / YAGNI，当前只抽象 Claude Code 与 Codex，不提前泛化更多平台。
- 优先标准库，避免新增外部依赖。
- 每个任务独立提交，保持可回滚与可审计。
