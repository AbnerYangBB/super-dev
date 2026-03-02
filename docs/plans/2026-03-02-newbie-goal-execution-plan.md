# super-dev 当前目标执行计划（新手闭环）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让小白用户可稳定完成 `fork -> 自定义能力 -> 安装/更新 -> 回退 -> 验证` 全流程。

**Architecture:** 继续采用“分发器（自然语言->intent->actions）+ 模板仓库 + 事务化 installer”的三层架构。优先补齐文档闭环与黑盒验证，再增强分发器的可表达能力，最后用 CI 固化回归门禁。

**Tech Stack:** Python 3（stdlib）、JSON/TOML、shell、Codex CLI、Claude Code CLI。

---

## Workstream 1：README 新手闭环重写（最高优先级）

**目标**
1. 小白读完 README 后无需理解源码即可完成安装、更新、回退、能力自定义。
2. README 信息层次明确：先上手、再原理、最后贡献。

**Files**
- Modify: `README.md`
- Modify: `common/install/INSTALL.md`
- Modify: `common/install/ROLLBACK.md`
- Modify: `CONTRIBUTING.md`

**任务**
1. 增加“10 分钟上手”章节（前置条件、1 条命令路径、成功标志）。
2. 增加“fork 后自定义能力”章节（分发器命令 + 示例 + 常见边界）。
3. 增加“更新流程”章节（重复执行安装即更新，如何识别 `txn_id/state_file`）。
4. 增加“常见问题”章节（尤其 Claude CLI 必须在目标项目 cwd 执行）。
5. 贡献指南补充“最小 PR 验收清单”。

**验收标准**
1. 新手按 README 命令可在空项目完成 codex/claude 安装。
2. 新手可按 README 完成一次更新与回退。

---

## Workstream 2：分发器“自由添加能力”增强（功能优先）

**目标**
1. 从当前关键词匹配升级到“可提取关键参数”的规则解析（仍保持可预测）。
2. 支持更真实的能力描述，不局限于示例值（如 `example-server`）。

**Files**
- Modify: `.agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py`
- Modify: `common/install/scripts/portable_dispatch.py`
- Modify: `common/platforms/intents/schema.json`
- Modify: `common/platforms/intents/examples/pre-commit-sync-loc.json`
- Modify: `tests/verification/skill_blackbox_cases.json`
- Create/Modify: `tests/portable_config/test_portable_dispatch.py`
- Modify: `README.md`（识别边界同步）

**任务**
1. 为 MCP 解析 server 名、command、args（至少支持 `name` 与 `command`）。
2. 为 hook 解析 trigger 与执行命令（支持预提交最小场景）。
3. 支持平台目标限定（仅 codex / 仅 claude / 双平台）。
4. 将“删除语义暂不支持”作为显式错误/提示返回，不静默降级。
5. 扩展黑盒用例覆盖参数化输入。

**验收标准**
1. 新增黑盒用例全部通过。
2. 生成结果中不再硬编码 `example-server`，而是来自输入。

---

## Workstream 3：安装/更新体验固化（流程优先）

**目标**
1. 降低“命令拼装错误”概率，让用户更难用错目录和参数。
2. 把 fork 场景与本地模板根路径作为一等路径写清楚。

**Files**
- Modify: `common/install/INSTALL.md`
- Create: `scripts/install_from_template.sh`（可选）
- Create: `scripts/update_from_template.sh`（可选）
- Modify: `tests/verification/test_installer_e2e.py`

**任务**
1. INSTALL 增加“本地 fork 作为 template-root”的官方步骤。
2. 增加“更新=重复安装同 profile”明确说明与示例。
3. 增加“错误目录执行”防呆提示（文档与脚本提示）。

**验收标准**
1. 在临时目标项目执行安装与更新均输出 `status=ok`。
2. `state_file` 路径符合 profile 预期。

---

## Workstream 4：CLI 黑盒测试产品化（关键验证）

**目标**
1. 让“Codex/Claude 真机 CLI 行为”成为可复现验证，而非一次性手工测试。
2. 固化 cwd、权限、add-dir 等关键参数。

**Files**
- Create: `scripts/verification/run_agent_cli_blackbox.sh`（或 `.py`）
- Create: `tests/verification/test_agent_cli_blackbox.py`（可选，按环境跳过）
- Modify: `docs/verification/skill-blackbox-protocol.md`

**任务**
1. 抽象黑盒脚本：准备 fork、副本项目、执行安装更新回退、汇总 JSON 报告。
2. 报告包含：退出码、关键文件存在性、关键内容证据、事务信息。
3. 文档明确：Claude 需在目标项目目录执行。

**验收标准**
1. 一条命令产出完整报告。
2. 报告可直接判断通过/失败，不依赖人工解释。

---

## Workstream 5：门禁与发布节奏（质量兜底）

**目标**
1. 把核心验证命令变成“合并前必过”门禁。
2. 形成稳定发布节奏，避免文档与实现漂移。

**Files**
- Modify/Create: `.github/workflows/*.yml`
- Modify: `CONTRIBUTING.md`

**任务**
1. CI 至少执行 `scripts/verification/run_all.sh`。
2. 将 skill 黑盒加入 CI（或在无 CLI 环境下做脚本黑盒门禁）。
3. CONTRIBUTING 增加“提交前必跑命令”清单。

**验收标准**
1. PR 无法在关键验证失败时合并（按仓库策略配置）。
2. 文档与测试要求一致，且可一键执行。

---

## 推荐执行顺序（当前）

1. **先做 Workstream 1**：让新手闭环文档可直接跑通。
2. **并行做 Workstream 4**：把 CLI 黑盒变成标准化报告工具。
3. **再做 Workstream 2**：增强“自由添加能力”的表达力。
4. **随后做 Workstream 3**：把安装/更新体验再压平。
5. **最后做 Workstream 5**：CI 门禁收口。

---

## 本轮立即开工清单（今天）

1. 重写 `README.md` 的“10 分钟上手 + fork 自定义 + 更新 + 回退 + FAQ”。
2. 新建 `run_agent_cli_blackbox` 脚本，复用已验证参数组合。
3. 扩展 `skill_blackbox_cases.json`，覆盖“参数化 MCP/hook”。
4. 跑验证：
   - `bash scripts/verification/run_all.sh`
   - `python3 scripts/verification/run_skill_blackbox.py --repo-root . --cases tests/verification/skill_blackbox_cases.json --pretty`
