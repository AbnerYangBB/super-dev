# super-dev AGENTS Playbook

## 1. 项目北极星（不可偏离）
1. 这是一个可移植 AI 工程配置仓库，当前聚焦 iOS + `codex-cli` + `claude-code`。
2. 小白用户应能完成完整闭环：
   `fork` 仓库 -> 用内置 `platform-feature-dispatcher` 添加能力 -> 安装/更新到目标项目 -> 可回退。
3. 分发器职责是：`自然语言 -> intent -> actions -> 模板变更`，不直接改用户业务代码。
4. installer 职责是：仅改 AI 配置文件，保留用户已有配置，支持事务记录与回退。

## 2. 成功标准（Definition of Done）
1. 文档可用性：
   `README.md` 必须让小白理解 4 件事：项目做什么、如何安装、如何自定义能力、如何贡献。
2. 能力链路可用性：
   fork 后可用 `.agents/skills/platform-feature-dispatcher` 生成模板变更，并可通过安装命令落地到目标项目。
3. 双平台可用性：
   `codex-cli` 与 `claude-code` 都能执行安装/更新，并产出预期文件与状态记录。
4. 回退可用性：
   `portable_rollback.py` 能回退最近事务，输出 `status=ok`。
5. 验证可复现：
   自动化测试与 skill 黑盒验证必须通过。

## 3. 开发原则（执行顺序）
1. 先改规则与模型，再改模板：
   优先改 `common/platforms/capabilities/*`、`common/platforms/intents/*`。
2. 先 dry-run，再落盘：
   先跑分发器 `--dry-run`，确认 action 正确再生成模板。
3. 先验证，再宣称完成：
   至少执行一轮契约/模板/installer 验证和 skill 黑盒验证。
4. 文档同步更新：
   行为变化必须同步更新 `README.md`、`common/install/INSTALL.md`、必要时 `ROLLBACK.md` 与 `CONTRIBUTING.md`。

## 4. 标准命令清单

### 4.1 分发器（自然语言 -> 模板）
```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "增加一个 MCP server: example-server" \
  --dry-run \
  --pretty
```

```bash
python3 .agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py \
  --repo-root . \
  --prompt "增加一个 Hook: 提交前使用 sync-add-ios-loc 做本地化校验" \
  --pretty
```

### 4.2 模板生成（intent -> 模板）
```bash
python3 common/install/scripts/portable_generate_templates.py \
  --repo-root . \
  --intent-file common/platforms/intents/examples/pre-commit-sync-loc.json \
  --pretty
```

### 4.3 自动化验证
```bash
bash scripts/verification/run_all.sh
```

```bash
python3 scripts/verification/run_skill_blackbox.py \
  --repo-root . \
  --cases tests/verification/skill_blackbox_cases.json \
  --pretty
```

### 4.4 本地安装（目标项目中执行）
```bash
python3 /path/to/super-dev/common/install/scripts/portable_apply.py \
  --project-root "$PROJECT_ROOT" \
  --template-root "/path/to/super-dev" \
  --profile codex-ios \
  --namespace super-dev
```

```bash
python3 /path/to/super-dev/common/install/scripts/portable_apply.py \
  --project-root "$PROJECT_ROOT" \
  --template-root "/path/to/super-dev" \
  --profile claude-ios \
  --namespace super-dev
```

### 4.5 回退
```bash
python3 /path/to/super-dev/common/install/scripts/portable_rollback.py \
  --project-root "$PROJECT_ROOT"
```

## 5. 黑盒验证准则（真实小白行为模拟）
1. 必须在“模板仓库目录”和“目标项目目录”分离条件下测试。
2. Codex 调用建议：
```bash
codex exec -C "$TARGET_PROJECT" -s workspace-write --add-dir "$TEMPLATE_ROOT" -- "<prompt>"
```
3. Claude 调用建议（关键是 cwd）：
```bash
(cd "$TARGET_PROJECT" && \
  claude -p --permission-mode bypassPermissions --dangerously-skip-permissions \
  --add-dir "$TEMPLATE_ROOT" -- "<prompt>")
```
4. 验收时至少检查：
   - `status=ok`
   - 目标文件存在（`AGENTS.md` / `CLAUDE.md` / `.codex/config.toml` / `.claude/settings.json` / `.mcp.json` / skills 目录）
   - state 文件存在（`.codex/portable/state.json` 或 `.claude/portable/state.json`）

## 6. 已验证经验与坑位
1. `claude -p` 会以当前工作目录为项目根；若不 `cd` 到目标项目，可能把文件写到错误目录。
2. `codex exec` 子命令参数与顶层参数不完全一致，需按 `codex exec --help` 使用。
3. 当前分发器是规则识别，不是通用自然语言理解；复杂语义需手工改 intent。
4. 当前 `skill` 分发是目录增量同步，不是按 skill 名精确选择单个 skill。
5. 对 `codex-cli` 的 hook 目前走指令回退（写入 `AGENTS.md`），不是原生 hook 配置。

## 7. 每次交付前自检清单
1. 我是否证明了“小白闭环”仍可运行（新增能力 -> 安装/更新 -> 回退）？
2. 我是否保留了“仅改 AI 配置文件”的边界？
3. 我是否跑了可复现验证命令并记录结果？
4. 我是否更新了必要文档，避免下一个 Agent 失去目标和标准？
