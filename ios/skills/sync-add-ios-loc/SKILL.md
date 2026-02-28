---
name: sync-add-ios-loc
description: iOS 本地化增量同步工作流。用于代码迭代后自动识别需本地化字符串，生成/确认 Key，更新 zh-Hans 基准文件，并将新增/修改 Key 增量同步到其他语言文件（不整文件重排）。
---

# /sync-add-ios-loc 指令

## 适用场景
- 代码生成后，新增/修改了用户可见文案（toast、按钮、标题、提示语等）。
- 需要把新增文案纳入 iOS `Localizable.strings`。
- 需要同步多语，但**禁止整文件重排**、禁止批量回填覆盖历史翻译。

## 目标
1. 自动发现本次改动中“需要本地化”的字符串。
2. 形成可确认的`本地化实体集合`（Key / Value / Status）。
3. 仅对本次新增/修改 Key 进行处理并落地。
4. 增量同步到其他语言文件，保留原有顺序和翻译。

## 核心约束
- 默认基准文件：`zh-Hans.lproj/Localizable.strings`。
- 若用户未指定，必须先定位默认基准文件路径并检查命名风格。
- 同步脚本必须是**按 Key 增量修改**，不能整文件重排。
- Value 中双引号必须转义为 `\"`。
- 对“需本地化候选项”先确认再落地，避免误收录开发日志/调试文本。

## 本地化实体模型
每条记录称为一个`本地化实体`：
```json
{
  "key": "voice_translate_fail_retry_str",
  "value": "翻译失败，请重试",
  "status": "新增",
  "source": "path/to/file.swift:123"
}
```
- `status` 只允许：`新增` / `修改` / `删除`

## 执行流程

### 1. 定位基准文件与命名风格
- 默认路径：
  - `Packages/HelloExpertUI/Sources/HelloExpertUIBase/Resources/Localizable/zh-Hans.lproj/Localizable.strings`
- 若项目有多套基准文件，优先用户指定；否则按默认。
- 观察基准命名风格（例如 `intlXxx`、`voice_xxx`、snake_case），新增 Key 必须保持一致。

### 2. 用 git diff 识别本次本地化改动
优先使用脚本自动提取候选：
```bash
python3 scripts/detect_loc_entities.py \
  --repo-root /path/to/repo \
  --base-file Packages/HelloExpertUI/Sources/HelloExpertUIBase/Resources/Localizable/zh-Hans.lproj/Localizable.strings \
  --diff-ref HEAD \
  --output /tmp/loc_detect.json
```

脚本输出两类信息：
- `swift_entities`: Swift 代码里疑似需本地化实体（含 `.local` key 使用变化、硬编码候选）。
- `base_key_changes`: 基准文件里已有 key 的新增/修改/删除变化。

### 3. 组装“代码的实体集合”并确认
- 从 `/tmp/loc_detect.json` 合并实体，形成`代码的实体集合`。
- 对 `hardcoded_string_candidate` 必须人工确认（防误报）。
- 规则：
  - `新增`：代码新增用户可见文案且无现有 key。
  - `修改`：已有 key 的 value 语义调整。
  - `删除`：代码与基准都不再使用（通常不自动删，需人工决策）。

### 4. 为新增实体创建 Key
- 仅对 `status=新增` 创建 key。
- Key 必须符合基准风格（示例：`voice_not_clear_retry_str`）。
- 先尝试复用已有 key；只有语义不一致才新增。

### 5. 先更新基准文件（zh-Hans）
将确认后的实体写入一个 JSON（示例：`/tmp/loc_entities.json`）：
```json
{
  "entities": [
    {"key":"a_key","value":"中文文案","status":"新增"},
    {"key":"b_key","value":"更新后的中文文案","status":"修改"}
  ]
}
```

执行：
```bash
python3 scripts/update_base_loc.py \
  --base-file Packages/HelloExpertUI/Sources/HelloExpertUIBase/Resources/Localizable/zh-Hans.lproj/Localizable.strings \
  --entities-json /tmp/loc_entities.json
```

行为：
- 将本次 `修改` key 统一整理到 `(YB)` 区块。
- 将本次 `新增` key 统一整理到 `(YC)` 区块。
- 不做整文件重排。

### 6. 调用子 Agent 批量翻译
- 仅翻译 `新增` 和 `修改` 实体。
- 输入：中文 value + key + 目标语种。
- 输出：按语种拆分的实体 JSON（建议每语种一个文件）。

### 6.5 翻译结果校验（新增，强烈建议必做）
在写入目标语种前，先逐语种校验：
```bash
python3 scripts/validate_loc_translations.py \
  --source-entities /tmp/loc_entities.json \
  --translated-entities /tmp/loc_entities_<lang>.json \
  --target-lang <lang>
```

CI 或严格模式建议加 `--fail-on-warn`，校验未通过则停止同步：
```bash
python3 scripts/validate_loc_translations.py \
  --source-entities /tmp/loc_entities.json \
  --translated-entities /tmp/loc_entities_<lang>.json \
  --target-lang <lang> \
  --fail-on-warn
```

校验项：
- Key 集合一致（缺失 key 会报错）。
- 占位符一致（如 `%@`、`%d` 数量与类型一致）。
- 空值拦截（空翻译会报错）。
- 疑似未翻译告警（值与中文完全一致）。
- 长度异常告警（可通过参数调阈值）。

### 7. 按 key 增量同步到各语种
仅对“校验通过”的语种执行同步。对每个目标语言执行：
```bash
python3 scripts/sync_loc_incremental.py \
  --target-file Packages/HelloExpertUI/Sources/HelloExpertUIBase/Resources/Localizable/<lang>.lproj/Localizable.strings \
  --entities-json /tmp/loc_entities_<lang>.json
```

行为：
- `新增/修改`：按 key 替换或追加。
- 默认不删除 key（除非显式 `--apply-delete`）。
- 保持目标文件其余内容与顺序不变。

### 8. 校验
- 校验新增/修改 key 已写入 `zh-Hans` 与目标语种。
- 校验 `.strings` 语法合法（引号与分号）。
- 校验翻译占位符和 key 集合一致（建议使用 `validate_loc_translations.py` 预检）。
- 校验此次 diff 未出现“整文件重排”式噪音。

## Hook 模式（代码生成后自动触发）
用于外层流程（CI 或本地自动化）：
1. 生成代码后，先运行 `detect_loc_entities.py`。
2. 若检测到：
   - 新增硬编码候选，或
   - `.local` key 使用变化，或
   - 基准文件 key 变更
   则自动触发本 skill。
3. 本 skill执行后，再进入构建/测试步骤。

建议触发条件（伪代码）：
```bash
python3 scripts/detect_loc_entities.py ... --output /tmp/loc_detect.json
if jq '.swift_entities|length > 0 or (.base_key_changes.added|length + .base_key_changes.modified|length + .base_key_changes.deleted|length) > 0' /tmp/loc_detect.json; then
  # 调用 sync-add-ios-loc skill
fi
```

## 失败与回滚策略
- 如果翻译结果质量异常：只回滚目标语种文件，不回滚基准 zh-Hans。
- 如果检测结果误报：从实体集合中移除后重跑同步。
- 严禁使用“全量重排”脚本覆盖历史翻译。

## 附属资源
- `scripts/detect_loc_entities.py`
  - 从 git diff 提取本地化候选实体和基准 key 变更。
- `scripts/update_base_loc.py`
  - 增量更新 zh-Hans，并规范 YB/YC 区块。
- `scripts/sync_loc_incremental.py`
  - 对单个目标语言执行按 key 增量同步（不重排）。
- `scripts/validate_loc_translations.py`
  - 翻译后预检（key 集合、占位符、空值、疑似未翻译、长度异常）。
