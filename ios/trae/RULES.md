# super-dev Trae Rules

## 1) 沟通与基本原则
1. 注释、分析、回复统一使用中文，技术术语可保留英文。
2. 正常情况下优先复用现有能力：`MCP` > `skills` > 临时脚本。
3. 读取遵循最小必要原则，避免无差别全量扫描。

## 2) 分析与验证
1. 不确定 API 或框架用法时，优先校验官方文档。
2. 复杂问题拆分后执行，先说明影响范围，再实施改动。
3. 完成改动后必须明确验证结果与未验证项。

## 3) iOS 构建与运行
1. 优先使用 `xcode-builder` skill 做构建验证。
2. 运行 App 优先使用 `ios-device-runner` skill，默认真机运行。

## 4) 本地化与提交
1. 涉及用户可见文案变更时，必须使用 `sync-add-ios-loc` skill。
2. 本地化同步要求：`zh-Hans` 基准、按 key 增量更新、禁止整文件重排覆盖历史翻译。
3. 提交信息遵循仓库既有风格（如 `feat/fix/bugfix/refactor`），内容不超过 20 个字。

# BEGIN SUPER-DEV DISPATCH:ios_loc_pre_commit_check:trae-ide:0
[pre_commit] skill:sync-add-ios-loc: validate localization before commit
# END SUPER-DEV DISPATCH:ios_loc_pre_commit_check:trae-ide:0
