/* ============================================================
 * PinSpec · popup
 * 模式开关、统计、导出 Prompt/JSON/Markdown、导入、清空、环境自检与权限引导
 * ============================================================ */
var SKILL = 'pinspec-annotations';
var K_MODE = 'ps_mode', K_ANNS = 'ps_anns', K_CONTINUOUS = 'ps_continuous';
var activeTab = null;

function $(id){ return document.getElementById(id); }
function toast(m){ var t=$('toast'); t.textContent=m; t.classList.add('show'); setTimeout(function(){ t.classList.remove('show'); }, 1800); }

/* 仅向顶层 frame 发消息，并吞掉 lastError，避免 popup 报 Unchecked runtime.lastError */
function tabMsg(tabId, msg, cb){
  chrome.tabs.sendMessage(tabId, msg, { frameId: 0 }, function(resp){
    void chrome.runtime.lastError;
    if (cb) cb(resp);
  });
}

/* ---- 初始化 ---- */
chrome.storage.local.get([K_MODE, K_ANNS, K_CONTINUOUS], function(d){
  $('modeCb').checked = !!d[K_MODE];
  $('continuousCb').checked = !!d[K_CONTINUOUS];
  $('stTotal').textContent = (d[K_ANNS] || []).length;
});
chrome.tabs.query({ active:true, currentWindow:true }, function(tabs){
  activeTab = tabs[0];
  runChecks();
});

/* ---- 模式开关 ---- */
$('modeCb').addEventListener('change', function(){
  var o = {}; o[K_MODE] = this.checked; chrome.storage.local.set(o);
  toast(this.checked ? '已开启标记模式' : '已关闭标记模式');
});

$('continuousCb').addEventListener('change', function(){
  var o = {}; o[K_CONTINUOUS] = this.checked; chrome.storage.local.set(o);
  toast(this.checked ? '已开启连续标记' : '已关闭连续标记');
});

/* ---- 面板 / 导出 / 导入 / 清空 ---- */
$('panelBtn').onclick = function(){
  if (!activeTab) return;
  ensureInjected(activeTab.id, function(resp){
    if (!resp){ toast('当前页面未注入，见下方自检'); return; }
    tabMsg(activeTab.id, { type:'ps-open-panel' }, function(){ window.close(); });
  });
};
$('promptBtn').onclick = function(){ copyPrompt(); };
$('expJson').onclick = function(){ exportData('json'); };
$('expMd').onclick = function(){ exportData('md'); };
$('impBtn').onclick = function(){ $('importFile').click(); };
$('importFile').addEventListener('change', function(e){
  var f = e.target.files[0]; if(!f) return;
  var rd = new FileReader();
  rd.onload = function(){
    try {
      var data = JSON.parse(rd.result);
      var incoming = Array.isArray(data) ? data : (data.annotations || []);
      chrome.storage.local.get([K_ANNS], function(d){
        var cur = d[K_ANNS] || [];
        var ids = {}; cur.forEach(function(a){ ids[a.id]=1; });
        incoming.forEach(function(a){ if(a && a.id && !ids[a.id]) cur.push(a); });
        var o={}; o[K_ANNS]=cur; chrome.storage.local.set(o, function(){ $('stTotal').textContent=cur.length; toast('已导入 '+incoming.length+' 条'); });
      });
    } catch(err){ toast('文件解析失败'); }
  };
  rd.readAsText(f);
});
$('clrBtn').onclick = function(){
  if (!confirm('确定清空全部备注？')) return;
  var o={}; o[K_ANNS]=[]; chrome.storage.local.set(o, function(){ $('stTotal').textContent='0'; $('stPage').textContent='0'; toast('已清空'); });
};

/* ---- 导出为 Prompt（复制到剪贴板） ---- */
function buildPrompt(list){
  var json = JSON.stringify({ tool:'PinSpec', skill:SKILL, total:list.length, annotations:list }, null, 2);
  return [
    '你是一名前端工程师，负责根据用户的可视化标记反馈修改网页 / 原型源码。',
    '',
    '下面是用户用 PinSpec 标记器导出的反馈数据（JSON）。请使用名为 `' + SKILL + '` 的 skill 来解析这份 JSON 并执行修复；',
    '该 skill 说明了字段含义、元素定位规则（selector 优先、tag+target 文本兜底）、以及 url→源文件 的映射方法。',
    '',
    '执行要求：',
    '1. 逐条处理 annotations：按 selector / tag / target / html 定位元素，依据 note 修改。',
    '2. 通过 url / page 字段定位到对应的源文件再修改。',
    '3. 改完后逐条回报：改了哪个文件、哪个元素、做了什么。',
    '',
    '```json',
    json,
    '```'
  ].join('\n');
}
function copyPrompt(){
  chrome.storage.local.get([K_ANNS], function(d){
    var anns = d[K_ANNS] || [];
    if (!anns.length){ toast('还没有备注'); return; }
    var text = buildPrompt(anns);
    navigator.clipboard.writeText(text).then(function(){ toast('Prompt 已复制，粘贴给 AI 即可'); }, function(){ toast('复制失败，请改用导出 JSON'); });
  });
}

function exportData(kind){
  chrome.storage.local.get([K_ANNS], function(d){
    var anns = d[K_ANNS] || [];
    if (!anns.length){ toast('还没有备注'); return; }
    var name, text, type;
    if (kind === 'json'){
      name='annotations.json'; type='application/json';
      text=JSON.stringify({ tool:'PinSpec', skill:SKILL, generatedAt:new Date().toISOString(), total:anns.length, annotations:anns }, null, 2);
    } else {
      name='annotations.md'; type='text/markdown';
      var byPage={}; anns.forEach(function(a){ (byPage[a.page]=byPage[a.page]||[]).push(a); });
      text='# 原型标记反馈\n\n';
      Object.keys(byPage).forEach(function(pg){ text+='## '+pg+'\n\n'; byPage[pg].forEach(function(a){ text+='- `'+(a.selector||'')+'` '+(a.target?('“'+a.target+'”'):'')+'\n  - 备注：'+a.note+'\n'; }); text+='\n'; });
    }
    var blob=new Blob([text],{type:type}), url=URL.createObjectURL(blob);
    var a=document.createElement('a'); a.href=url; a.download=name; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    toast('已导出 '+name);
  });
}

/* ---- 确保 content script 已注入（失败则用 scripting 自动补注入，免刷新） ---- */
function ensureInjected(tabId, cb){
  tabMsg(tabId, { type:'ps-ping' }, function(resp){
    if (resp){ cb(resp); return; }
    if (!chrome.scripting){ cb(null); return; }
    // 当前页未注入：主动注入一次（file:// 需已开启文件访问，否则注入会被拒绝）
    chrome.scripting.insertCSS({ target:{ tabId:tabId, allFrames:true }, files:['content.css'] }).catch(function(){});
    chrome.scripting.executeScript({ target:{ tabId:tabId, allFrames:true }, files:['content.js'] }).then(function(){
      tabMsg(tabId, { type:'ps-ping' }, function(r2){ cb(r2 || null); });
    }, function(){ cb(null); });
  });
}

/* ---- 环境自检 ---- */
function addCheck(state, html){
  var icon = state==='ok'?'✓':(state==='warn'?'!':'×');
  var div=document.createElement('div'); div.className='chk';
  div.innerHTML='<span class="ic '+state+'">'+icon+'</span><span class="tx">'+html+'</span>';
  $('checks').appendChild(div);
}
function runChecks(){
  $('checks').innerHTML='';
  $('guideFile').classList.remove('show');
  $('guideDead').classList.remove('show');
  var url = activeTab ? (activeTab.url || '') : '';
  var isFile = url.indexOf('file://') === 0;
  var isRestricted = /^(chrome|edge|about|chrome-extension|https:\/\/chrome\.google\.com\/webstore|https:\/\/chromewebstore\.google\.com)/.test(url);

  if (isRestricted){ addCheck('no', '当前是浏览器受限页面，扩展无法在此运行。请切到目标网页。'); $('guideDead').classList.add('show'); return; }
  if (!activeTab){ addCheck('no','未获取到当前标签页。'); return; }

  // 以「是否注入成功」为唯一权威结论；失败时自动尝试补注入
  ensureInjected(activeTab.id, function(resp){
    if (resp){
      addCheck('ok', '标记器已就绪，当前页面 <b>'+resp.page+'</b>。' + (isFile ? '（file:// 文件访问已开启）' : '（http/https）'));
      $('stPage').textContent = resp.mine || 0;
    } else if (isFile){
      addCheck('no', '无法在此 <b>file://</b> 页面注入：请开启「允许访问文件网址」后<b>重新打开此弹窗</b>。');
      $('guideFile').classList.add('show');
    } else {
      addCheck('no', '未能注入标记器：请<b>刷新页面</b>后重试（该页面可能限制脚本注入）。');
      $('guideDead').classList.add('show');
    }
  });
}

/* ---- 打开扩展设置页（引导开启文件访问） ---- */
$('openSettings').onclick = function(){
  chrome.tabs.create({ url: 'chrome://extensions/?id=' + chrome.runtime.id });
};
$('copyCmd').onclick = function(){
  navigator.clipboard.writeText($('serveCmd').textContent).then(function(){ toast('命令已复制'); });
};
