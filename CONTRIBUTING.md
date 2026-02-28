# Contributing

感谢关注本仓库。

## 当前策略

- 本仓库目前仅用于自用，功能路线以作者需求为先。
- 外部 PR 可能被延后处理或不合并，请理解。

## 提交流程建议

1. 先提 issue 说明背景与目标。
2. 变更保持最小化，避免引入与目标无关的重构。
3. 需要补充对应测试（安装/回退/文档约束）。
4. 提交前运行：

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## 文档要求

- 涉及行为变更时，需同步更新 `README.md` 和 `common/install/*.md`。
