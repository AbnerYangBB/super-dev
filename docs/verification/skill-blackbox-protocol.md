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

## 子 Agent CLI 验证（会话级）

除脚本黑盒外，建议在会话中使用子 agent CLI 再跑一遍典型用例：

1. `spawn_agent` 启动执行 agent。
2. `send_input` 投递自然语言需求。
3. `wait` 等待完成并抓取结果。
4. 对照文件变更与 `blackbox-report.json` 交叉验证。

该步骤用于证明：不仅脚本可执行，代理协作流程也能稳定触发同一结果。
