# PinSpec — 通用网页/原型标记器（Chrome 扩展）

在**任意网页或原型页面**上选中具体元素写备注，可视化标记，并导出结构化反馈（JSON / Markdown / AI Prompt）交给开发或 AI Agent。
content script 直接访问页面真实 DOM，元素选择稳定可靠，且适用于 `http(s)` 与 `file://` 任意站点，不限于本仓库原型。

---

## 一、安装

1. 打开 `chrome://extensions`
2. 右上角开启 **开发者模式**
3. 点 **加载已解压的扩展程序**，选择本目录 `annotator-extension/`
4. 工具栏出现 **PinSpec**，点击图标即可打开控制面板（popup）

## 二、在哪些页面可用

- ✅ 任意 `http` / `https` 网页
- ✅ `file://` 本地 HTML —— 只需在扩展详情里开启 **允许访问文件网址**（一次性）
- ❌ `chrome://`、Chrome 应用商店等浏览器受限页面（无法注入，属浏览器限制）

> **本地服务器不是必需的。** 标记器在 `file://` 下完全可用，开启文件访问即可。
> 本地服务器只是「可选」便利：免去文件访问开关，并让原型外壳 `index.html` 的「后退/标题同步」生效（`file://` 下浏览器禁止父页读取跨域 iframe，故该两项失效，但导航与标记不受影响）。
> ```bash
> cd <仓库根目录> && python3 -m http.server 8000   # 可选
> # http://localhost:8000/dev-docs/mvp-prototype/
> ```

> 开启「允许访问文件网址」后**无需手动刷新已打开的页面**：再次点开 PinSpec 弹窗时，会通过 `chrome.scripting` 自动补注入当前页。

## 三、标记工作流

1. 在页面里导航到目标位置
2. 点 PinSpec 图标 → 打开 **标记模式**（或按 `Alt/⌥ + Shift + M`）
3. 元素悬停高亮，**点击**任意元素 → 元素旁浮层写备注 → 保存
   - 保存后**默认自动退出标记模式**；在 popup 开启「连续标记」后可连续添加
4. 已标记元素显示红框 + 编号图钉；右下角**可拖动悬浮球**点击打开侧边栏，可查看 / 跳转 / 编辑 / 删除
5. 交给 AI：点 **导出为 Prompt（复制给 AI）**，直接粘贴到 Agent 对话即可
   - 也可 **导出 JSON / Markdown** 得到文件

## 四、和 AI Agent 协作（核心）

「**导出为 Prompt**」会把 **AI 提示词 + 标记 JSON** 一起复制到剪贴板，提示词里明确要求 AI 使用
[`pinspec-annotations`](../../../.agents/skills/base/pinspec-annotations/SKILL.md) skill 来解析数据并修复原型。

- 配套 skill 路径：`.agents/skills/base/pinspec-annotations/SKILL.md`
- skill 说明了字段含义、元素定位规则（selector 优先、tag+target 文本兜底）、`url → 源文件` 映射，让 Agent 直接据此改源码。

## 五、产品设计要点（扩展限制与对策）

| 限制 | 对策 |
| --- | --- |
| `file://` 默认不注入脚本 | popup 自检 + 一键跳设置页引导开启「允许访问文件网址」；同时推荐本地服务器 |
| `chrome://`、应用商店等受限页无法运行 | 自检识别并提示切换页面 |
| 装完扩展旧标签页未注入 | 自检提示刷新页面 |
| 悬浮球可能挡住页面内容 | 安装后始终显示，**可拖动**到任意位置，位置跨页记忆 |
| 子框架（设备外壳内 iframe）需覆盖 | `all_frames: true` 注入，每帧独立选元素 |
| 多帧 / 多页数据需共享 | 统一存 `chrome.storage.local`，按 URL 分组，`storage.onChanged` 实时同步 |
| 选择器在 DOM 变化后失效 | selector + tag/target 文本兜底 + html 片段确认；滚动/变更时 rAF 重定位图钉 |
| 非安全上下文 (`http`) 剪贴板 API 受限 | Prompt 复制带 `execCommand` 兜底 |

## 六、导出 JSON 格式

```json
{
  "tool": "PinSpec",
  "skill": "pinspec-annotations",
  "generatedAt": "2026-06-18T08:00:00.000Z",
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
      "ts": "2026-06-18T08:00:00.000Z"
    }
  ]
}
```

- `selector` / `tag` / `target` / `html`：定位与确认元素的依据
- `note`：用户的修改意见（唯一权威诉求）

## 七、文件结构

```
annotator-extension/
├── manifest.json    # MV3 配置（权限 / file 匹配 / 快捷键 / 图标）
├── background.js    # service worker：快捷键切换、角标计数
├── content.js       # 注入脚本：选元素、浮层、红框图钉、可拖动悬浮球、面板、导出
├── content.css      # 注入样式（ps- 前缀，隔离宿主页面样式）
├── popup.html/js    # 控制面板：模式、连续标记、统计、导出 Prompt/JSON/MD、导入、环境自检
├── icons/icon.png   # 扩展图标
└── README.md
```
