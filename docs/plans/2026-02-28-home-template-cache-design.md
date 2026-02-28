# Home 级模板缓存重设计（避免项目残留）

- 日期：2026-02-28
- 背景：当前私有仓库 fallback 会把模板 clone 到项目内 `.codex/portable/template/super-dev`，可能造成提交污染。
- 目标：模板缓存迁移到 `$HOME` 级目录，支持 Codex/Claude/Web 共用同一模板源。

## 1. 设计目标

1. 模板仓库不再落到项目目录。
2. 默认缓存目录为 `$HOME/.super-dev/templates/super-dev`。
3. 保留项目内安装事务状态（`state/backups/history/conflicts`），因为这属于可回退能力必要数据。
4. 兼容公开仓库（raw）与私有仓库（本地读取 INSTALL/ROLLBACK）。
5. 未来新增 Claude/Web 时，不新增第二套模板仓库，仅新增 profile/manifest。

## 2. 路径模型

1. 环境变量：`SUPER_DEV_HOME`。
2. 默认值：`$HOME/.super-dev`。
3. 模板目录：`$SUPER_DEV_HOME/templates/super-dev`。

## 3. 安装与回退入口调整

### 3.1 INSTALL

1. 原流程：模板落在 `.codex/portable/template/super-dev`。
2. 新流程：模板落在 `$SUPER_DEV_HOME/templates/super-dev`。
3. 私有仓库 fallback 文案改为：
   - 先 clone/pull 到 HOME 模板目录。
   - 再读取 `$TEMPLATE_DIR/common/install/INSTALL.md`。

### 3.2 ROLLBACK

1. 原流程：从项目内模板路径执行 `portable_rollback.py`。
2. 新流程：从 HOME 模板路径执行。

## 4. 兼容与迁移

1. 不再默认使用旧路径 `.codex/portable/template/super-dev`。
2. 在 README 中增加迁移说明：旧目录可手动删除，避免误提交。
3. 安装与回退脚本 CLI 不改参数语义，只改文档和提示词入口路径。

## 5. 验收标准

1. 执行安装后，项目目录不出现模板 clone 残留。
2. 项目内仅出现 `.codex/portable/state|backups|history|conflicts` 及目标配置文件变更。
3. apply/rollback 端到端可用。
4. 单元测试与文档约束测试通过。
5. 远程验证（clone 远程仓库到 HOME 缓存）通过。
