# Contributing

感谢关注本仓库。

## 当前策略

- 本仓库目前仍以自用为主。
- 外部 PR 可能不会立即处理，请理解。
- 变更应围绕 `skills/` 内容、同步脚本或仓库说明展开，不要引入额外平台分发逻辑。

## 贡献边界

可以改：

- `skills/` 下的内容
- `scripts/sync_skills.py`
- `README.md`、`CONTRIBUTING.md`、`SECURITY.md`
- `.github/` 下与仓库说明或最小验证相关的文件

不要加回：

- 平台区分
- profile 安装器
- 回滚事务
- 分发器或模板生成器
- 会写入 `.agents/skills/super-dev/` 以外路径的逻辑

## 最小验证

提交前至少执行一次 dry-run 和一次真实同步：

```bash
python3 scripts/sync_skills.py --workspace-root /tmp/super-dev-verify --dry-run
python3 scripts/sync_skills.py --workspace-root /tmp/super-dev-verify
```

如果你改了文档或 `.github/`，还要确认它们没有残留旧模型表述，例如安装、回滚、多平台 profile。

## 文档同步要求

如果你的改动影响了行为边界或使用方式，请同步更新：

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `.github/` 中受影响的 issue template、PR template 或 workflow
