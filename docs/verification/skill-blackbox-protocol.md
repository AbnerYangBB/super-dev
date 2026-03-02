# Skill 黑盒验收协议

## 目标

验证 `platform-feature-dispatcher` skill 在真实输入下是否能输出正确平台动作，并把变更写到正确模板文件。

## 输入

- 用例集：`tests/verification/skill_blackbox_cases.json`
- 入口脚本：`.agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py`

## 校验项

1. `expected_actions`：平台动作是否匹配（platform/operation/target）。
2. `expected_changed_files`：是否写入了期望模板文件。
3. `evidence_patterns`：变更文件中是否出现关键证据文本。

## 执行命令

```bash
python3 scripts/verification/run_skill_blackbox.py \
  --repo-root . \
  --cases tests/verification/skill_blackbox_cases.json \
  --pretty
```

输出报告：`tests/verification/blackbox-report.json`

## Agent CLI 黑盒验证（推荐）

除脚本黑盒外，建议执行真实 `codex` / `claude` CLI 黑盒：

```bash
bash scripts/verification/run_agent_cli_blackbox.sh \
  --repo-root . \
  --pretty
```

可选参数：

1. `--skip-codex`：仅验证 Claude。
2. `--skip-claude`：仅验证 Codex。
3. `--output <path>`：指定 JSON 报告路径。
4. `--work-dir <dir>`：指定工作目录，不使用临时目录。

输出报告默认位于临时目录，包含：

1. fork 模板变更检查（能力分发是否生效）
2. Codex/Claude 安装、更新、回退退出码
3. 关键目标文件存在性检查
4. 命令输出尾部，便于排障

注意事项：

1. Claude CLI 必须在目标项目目录执行，否则可能写错路径。
2. 该黑盒依赖本机 `codex` / `claude` 可用且已登录。
