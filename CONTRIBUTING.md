# Contributing

感谢关注本仓库。

## 当前策略

- 本仓库目前仅用于自用，功能路线以作者需求为先。
- 外部 PR 可能被延后处理或不合并，请理解。

## 提交流程建议

1. 先提 issue 说明背景与目标。
2. 变更保持最小化，避免引入与目标无关的重构。
3. 需要补充对应测试（安装/回退/文档约束/分发器黑盒）。
4. 提交前运行：

```bash
bash scripts/verification/run_all.sh
python3 scripts/verification/run_skill_blackbox.py --repo-root . --cases tests/verification/skill_blackbox_cases.json --pretty
```

## 小白闭环验收（建议）

如改动涉及分发器、安装或文档，建议额外执行一次真实流程：

1. fork 副本中用 `platform-feature-dispatcher` 生成模板变更。
2. 在目标项目分别执行 `codex-ios` / `claude-ios` 安装。
3. 再执行一次安装作为更新。
4. 执行回退，确认 `status=ok`。

## 文档要求

- 涉及行为变更时，需同步更新 `README.md` 和 `common/install/*.md`。
- 涉及能力边界变化时，需同步更新 `README.md` 的“指令识别范围/能力边界/FAQ”。
