# AGENTS 协作规范

## 1) 沟通与基本原则
1. 注释、分析、回复统一使用中文，技术术语可保留英文。
2. 正常情况下优先复用现有能力：`MCP` > `skills` > 临时脚本。
3. 读取遵循最小必要原则，避免无差别全量扫描。

## 2) Serena激活原则
1. 会话启动时不用立即激活.
2. 在执行`文件/目录浏览和查找`, `symbol查找`, `引用关系查找`之前, 按以下顺序激活后方可使用(无需再次激活):
   `serena.activate_project` -> `serena.check_onboarding_performed` -> `serena.initial_instructions`。

## 3) 项目构建规则
1. 如果`xcode`这个mcp已经可用, 则优先使用, 否则使用 `xcode-builder`构建项目.
2. 优先使用 `ios-device-runner` 进行真机运行.

## 4) 本地化与提交
1. 提交代码时，若涉及用户可见文案变更，必须使用 `sync-add-ios-loc` skill。
2. 本地化同步要求：`zh-Hans` 基准、按 key 增量更新、禁止整文件重排覆盖历史翻译。
3. 提交信息遵循仓库既有风格（如 `feat/fix/bugfix/refactor`），内容不超过 20 个字。

## 5) 交付输出规范
1. 明确说明：改了什么、为什么改、影响哪些文件。
2. 明确说明：执行了哪些验证（编译/运行/测试）以及结果。
3. 明确说明：未执行项及原因（工具缺失、设备不可用、权限限制等）。

# BEGIN SUPER-DEV DISPATCH:ios_loc_pre_commit_check:trae-ide:0
[pre_commit] skill:sync-add-ios-loc: validate localization before commit
# END SUPER-DEV DISPATCH:ios_loc_pre_commit_check:trae-ide:0
