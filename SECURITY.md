# Security Policy

## Supported Versions

当前只维护 `main` 分支。

## Scope

本仓库的主要安全边界在于同步脚本 `scripts/sync_skills.py`。

它只应该：

- 读取仓库内的 `skills/`
- 写入目标工作区的 `.agents/skills/super-dev/`

它不应该：

- 写入业务代码
- 覆盖 `.agents/skills/` 下其他命名空间
- 跟随符号链接写到目标目录之外
- 删除 `.agents/skills/super-dev/` 之外的任何文件

## Reporting a Vulnerability

如发现以下问题，请不要公开提交 issue：

- 路径穿越
- 符号链接绕过
- 越权覆盖其他目录
- 命令注入
- 凭据泄漏风险

请通过维护者可见的私下渠道联系，并附上复现步骤、影响范围和环境信息。
