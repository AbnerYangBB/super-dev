---
name: pinspec-annotations
description: Parse PinSpec annotation exports (JSON or "Export as Prompt" output) and apply the requested fixes to web/prototype source. Use when the user pastes PinSpec feedback, an annotations.json with a "tool":"PinSpec" field, or asks to apply prototype markup/annotations to HTML/CSS source.
---

# pinspec-annotations

PinSpec 是一个通用网页/原型标记器（Chrome 扩展）。用户在页面上选中元素或整页写备注，导出为 JSON 或「Prompt」。
本 skill 说明如何**解析这份数据并把每条备注准确地落到源码**上。

## 触发场景

- 用户粘贴了带 `"tool": "PinSpec"` 的 JSON，或一段以「请使用 `pinspec-annotations` skill」开头的 Prompt。
- 用户给了 `annotations.json` / `annotations.md` 并要求据此修改原型。

## 数据结构

```jsonc
{
  "tool": "PinSpec",
  "skill": "pinspec-annotations",
  "total": 2,
  "annotations": [
    {
      "id": "a1718...",          // 唯一 ID
      "url": "file:///.../screens/map-home.html", // 标记时的页面 URL（定位源文件用）
      "page": "map-home",        // 页面名（通常是文件名去扩展名）
      "title": "地图首页",        // document.title
      "scope": "element",        // element=元素级 | page=整页级
      "selector": "div.toolbar > button:nth-of-type(2)", // CSS 选择器（首选定位依据）
      "tag": "button",           // 元素标签（兜底定位）
      "target": "添加地点",       // 元素可见文本（兜底定位，可能以 … 截断）
      "html": "<button class=...>添加地点</button>", // 截断的 outerHTML（确认匹配用）
      "note": "这个按钮挪到右上角，文案改成「新建」", // 用户的修改诉求（执行依据）
      "ts": "2026-06-18T08:00:00.000Z"
    }
  ]
}
```

## 工作流

复制此清单并逐步推进：

```
- [ ] 1. 解析 JSON，按 page / url 分组
- [ ] 2. 为每个 page 定位源文件
- [ ] 3. 逐条定位元素（selector → tag+target → html 确认）
- [ ] 4. 按 note 修改；scope=page 做整页级调整
- [ ] 5. 逐条回报改动
```

### 1. 定位源文件（url / page → 文件）

按可靠性优先：

1. **`file://` 的 url**：去掉 `file://` 前缀即为绝对路径，直接定位该 HTML 文件。
2. **`http(s)` 的 url**（如本地服务器 `http://localhost:8000/dev-docs/mvp-prototype/screens/map-home.html`）：取 host 之后的路径，相对仓库根定位文件。
3. **兜底**：用 `page` 字段（文件名）在仓库内搜索同名文件；若多处命中，用 `url` 的目录层级消歧。

> 找不到唯一源文件时，先列出候选并向用户确认，不要盲改。

### 2. 定位元素

1. 在源文件中用 `selector` 做 CSS 匹配（首选）。
2. 选择器失效时（DOM 结构与导出时不同），用 `tag` + `target` 文本匹配：找标签为 `tag` 且可见文本以 `target`（去掉末尾 `…`）开头的元素。
3. 用 `html` 片段确认命中的是同一个元素，避免误改同名/同文本的其他元素。

### 3. 应用修改

- `scope = "element"`：把 `note` 的诉求落到该元素（改文案、改样式、移动、删除等）。`note` 是自然语言，按工程师常识转成具体改动。
- `scope = "page"`：整页级调整（布局、配色、信息架构、新增/删除区块等）。
- 同一文件多条备注：一次性读文件、集中修改，减少重复读写。

### 4. 回报格式

每条备注按此格式回报：

```
- [page-name] <selector 或 整页>
  - 诉求：<note>
  - 改动：<文件路径> 第 X 行 …（具体做了什么）
```

## 注意

- `note` 是唯一权威诉求；`selector/tag/target/html` 只是定位线索，不要据它们臆测需求。
- 不确定的修改（涉及删除内容、改动交互逻辑、跨文件影响）先向用户确认再执行。
- 若导出数据来自非本仓库的任意网页，定位文件不适用时，直接向用户说明并请其提供源文件路径。
