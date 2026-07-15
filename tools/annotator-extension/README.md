# PinSpec — Chrome 网页标记器

PinSpec 是一个用于网页和 HTML 原型的可视化标记 Chrome 扩展。它可以在页面上选中具体元素、写备注、显示图钉标记，并把反馈导出为 JSON、Markdown 或可直接交给 AI Agent 的 Prompt。

当前版本：`v1.2.9`

## 功能概览

- 在页面元素上添加备注，备注会按 URL / 页面分组保存到 `chrome.storage.local`。
- 标记过的元素会显示描边和编号图钉，便于回看和定位。
- 页面右下角提供可拖动悬浮按钮，点击后打开右侧标注面板。
- 右侧面板支持查看、定位、编辑、删除、清空、导出 Prompt、导出 JSON、导出 MD。
- 默认只在本地页面启用：`file://`、`localhost`、`127.x.x.x`、`0.0.0.0`、`::1`。
- 需要在普通 `http(s)` 网站使用时，可在 popup 中开启「任何网址均加载」。
- 支持自定义「标记快捷键」，默认是 `⌥ + ⇧ + M`。
- 支持「连续标记」：保存备注后不自动退出标记状态。
- popup、悬浮按钮、右侧面板和备注浮层会自动跟随浏览器浅色 / 暗黑模式。

## 安装

1. 打开 `chrome://extensions`。
2. 右上角开启「开发者模式」。
3. 点击「加载已解压的扩展程序」。
4. 选择本目录：`tools/annotator-extension/`。
5. 工具栏出现 PinSpec 图标后，点击图标即可打开设置面板。

如果要标记 `file://` 本地 HTML，请进入扩展详情页并开启「允许访问文件网址」。

## Popup 设置

点击浏览器工具栏里的 PinSpec 图标，会看到以下设置：

- `当前标记状态`：显示当前页面是否处于标记状态。绿色为开启，红色为关闭。
- `标记快捷键`：右侧按钮显示当前快捷键。点击按钮后按下新的组合键即可自定义。
- `连续标记`：开启后，保存一条备注后仍保持标记状态。
- `任何网址均加载`：默认关闭。关闭时只在本地文件和本地网址启用；开启后普通 `http(s)` 网页也会显示悬浮按钮和右侧面板。
- `环境自检`：显示当前页面是否可用。成功显示「标记器已就绪」，失败显示「浏览器页面受限」。

## 使用流程

1. 打开要标记的页面。
2. 如果是本地 HTML 或本地服务器页面，PinSpec 默认可用；如果是普通网站，先在 popup 开启「任何网址均加载」。
3. 用 popup 或快捷键开启标记模式。
4. 鼠标悬停页面元素会出现高亮，点击目标元素。
5. 在弹出的备注框里填写修改意见，然后保存。
6. 页面会显示编号图钉，右下角悬浮按钮也会显示备注数量。
7. 点击悬浮按钮打开右侧标注面板，可查看、定位、编辑、删除或导出标注。

保存备注后默认会退出标记模式；如需连续标记多处内容，请开启「连续标记」。

## 右侧标注面板

右侧面板用于管理具体标记内容，popup 不再展示备注列表。

面板支持：

- `标记模式`：手动切换当前页面的标记状态，也会同步快捷键切换后的状态。
- 点击备注卡片：定位并高亮页面上的对应元素。
- `编辑`：重新打开备注输入浮层。
- `删除`：删除单条备注。
- `清空`：清空全部备注。
- `导出为 Prompt`：复制 AI Prompt 和标记 JSON 到剪贴板。
- `导出JSON`：下载 `annotations.json`。
- `导出MD`：下载 `annotations.md`。

## 和 AI Agent 协作

PinSpec 推荐配合 `pinspec-annotations` skill 使用。该 skill 会解析 PinSpec 导出的 JSON / Prompt，并根据 `selector`、`tag`、`target`、`html`、`url`、`page` 等字段定位源文件和元素。

配套 skill 路径：

`skills/design/pinspec-annotations/SKILL.md`

在 Cursor 中使用时，有两种推荐方式：

1. 点击右侧面板的「导出为 Prompt」，把复制出来的内容直接粘贴给 Agent。Prompt 内会说明使用 `pinspec-annotations` skill。
2. 导出 `annotations.json` 后，把 JSON 文件或内容交给 Agent，并明确说明：请使用 `pinspec-annotations` skill 解析并按备注修改源码。

Agent 处理时会按以下思路执行：

- 解析导出的 `annotations`。
- 按 `url` / `page` 定位源文件。
- 优先用 `selector` 定位元素。
- 如果 selector 失效，则用 `tag` + `target` 文本兜底。
- 用 `html` 片段辅助确认命中是否正确。
- 以 `note` 作为唯一权威修改诉求。

## 导出 JSON 格式

```json
{
  "tool": "PinSpec",
  "skill": "pinspec-annotations",
  "generatedAt": "2026-07-15T07:00:00.000Z",
  "total": 1,
  "annotations": [
    {
      "id": "a1718...",
      "url": "http://localhost:8000/dev-docs/mvp-prototype/screens/map-home.html",
      "page": "map-home",
      "title": "地图首页",
      "scope": "element",
      "selector": "div.toolbar > button:nth-of-type(2)",
      "tag": "button",
      "target": "添加地点",
      "html": "<button class=\"btn\">添加地点</button>",
      "note": "这个按钮挪到右上角，文案改成「新建」",
      "ts": "2026-07-15T07:00:00.000Z"
    }
  ]
}
```

字段说明：

- `url` / `page`：用于定位被标记的页面和源文件。
- `selector`：首选元素定位依据。
- `tag` / `target`：selector 失效时的兜底定位依据。
- `html`：辅助确认是否命中同一个元素。
- `note`：用户写下的修改诉求，是 AI 执行修改时最重要的字段。

## 可用范围和限制

- 默认启用范围：`file://`、`localhost`、`127.x.x.x`、`0.0.0.0`、`::1`。
- 普通 `http(s)` 网站：需要开启「任何网址均加载」。
- 浏览器受限页面不可用：`chrome://`、`edge://`、`about:`、Chrome Web Store、扩展自身页面等。
- `file://` 页面需要在 Chrome 扩展详情里开启「允许访问文件网址」。
- 扩展重新加载后，已打开页面里旧的 content script 可能仍存在；刷新页面即可加载最新版本。

## 文件结构

```text
annotator-extension/
├── manifest.json    # MV3 配置、权限、图标、注入脚本
├── background.js    # service worker：角标计数
├── content.js       # 注入脚本：标记、浮层、图钉、悬浮按钮、侧边栏、导出
├── content.css      # 注入样式，含浅色 / 暗黑模式
├── popup.html       # 插件设置页
├── popup.js         # 设置页逻辑
├── icons/           # 扩展图标
└── README.md
```
