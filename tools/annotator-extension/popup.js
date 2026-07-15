/* ============================================================
 * PinSpec · popup
 * 设置：标记模式、连续标记、单一标记快捷键、环境自检
 * ============================================================ */
var K_MODE = 'ps_mode', K_CONTINUOUS = 'ps_continuous', K_SHORTCUT = 'ps_custom_shortcut', K_ALL_URLS = 'ps_all_urls';
var activeTab = null;
var recordingShortcut = false;
var toastTimer = null;
var currentShortcut = null;
var allUrlsEnabled = false;
var modeOn = false;
var checkRunId = 0;

var DEFAULT_SHORTCUT = {
  code: 'KeyM',
  key: 'M',
  ctrlKey: false,
  altKey: true,
  shiftKey: true,
  metaKey: false
};

function $(id){ return document.getElementById(id); }

function toast(m){
  var t = $('toast');
  t.textContent = m;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ t.classList.remove('show'); }, 1800);
}

function storageObj(key, value){
  var o = {};
  o[key] = value;
  return o;
}

/* 仅向顶层 frame 发消息，并吞掉 lastError，避免 popup 报 Unchecked runtime.lastError */
function tabMsg(tabId, msg, cb){
  chrome.tabs.sendMessage(tabId, msg, { frameId: 0 }, function(resp){
    void chrome.runtime.lastError;
    if (cb) cb(resp);
  });
}

/* ---- 初始化 ---- */
chrome.storage.local.get([K_MODE, K_CONTINUOUS, K_SHORTCUT, K_ALL_URLS], function(d){
  modeOn = !!d[K_MODE];
  $('continuousCb').checked = !!d[K_CONTINUOUS];
  allUrlsEnabled = !!d[K_ALL_URLS];
  $('allUrlsCb').checked = allUrlsEnabled;
  renderShortcut(d[K_SHORTCUT] || DEFAULT_SHORTCUT);
  refreshModeStatus();
  if (activeTab) runChecks();
});

chrome.tabs.query({ active:true, currentWindow:true }, function(tabs){
  activeTab = tabs[0];
  refreshModeStatus();
  runChecks();
});

chrome.storage.onChanged.addListener(function(changes, area){
  if (area !== 'local') return;
  if (changes[K_MODE]){ modeOn = !!changes[K_MODE].newValue; refreshModeStatus(); }
  if (changes[K_CONTINUOUS]) $('continuousCb').checked = !!changes[K_CONTINUOUS].newValue;
  if (changes[K_SHORTCUT]) renderShortcut(changes[K_SHORTCUT].newValue || DEFAULT_SHORTCUT);
  if (changes[K_ALL_URLS]){
    allUrlsEnabled = !!changes[K_ALL_URLS].newValue;
    $('allUrlsCb').checked = allUrlsEnabled;
    refreshModeStatus();
    runChecks();
  }
});

/* ---- 模式状态 ---- */
function refreshModeStatus(){
  updateModeStatus(!!modeOn && isCurrentPageAllowed());
}

function updateModeStatus(on){
  var el = $('modeStatus');
  el.textContent = on ? '开启' : '关闭';
  el.classList.toggle('on', !!on);
}

$('continuousCb').addEventListener('change', function(){
  chrome.storage.local.set(storageObj(K_CONTINUOUS, this.checked));
  toast(this.checked ? '已开启连续标记' : '已关闭连续标记');
});

$('allUrlsCb').addEventListener('change', function(){
  allUrlsEnabled = this.checked;
  chrome.storage.local.set(storageObj(K_ALL_URLS, this.checked), function(){
    toast(allUrlsEnabled ? '已允许任何网址加载' : '已恢复仅本地加载');
    runChecks();
  });
});

function setMode(on){
  chrome.storage.local.set(storageObj(K_MODE, !!on));
  toast(on ? '已开启标记模式' : '已关闭标记模式');
}

/* ---- 单一标记快捷键 ---- */
function prettyModifier(name){
  if (name === 'meta') return '⌘';
  if (name === 'alt') return '⌥';
  if (name === 'ctrl') return '⌃';
  return '⇧';
}

function prettyKey(ev){
  if (/^Key[A-Z]$/.test(ev.code)) return ev.code.slice(3);
  if (/^Digit[0-9]$/.test(ev.code)) return ev.code.slice(5);
  var names = {
    Space: 'Space',
    Escape: 'Esc',
    ArrowUp: 'ArrowUp',
    ArrowDown: 'ArrowDown',
    ArrowLeft: 'ArrowLeft',
    ArrowRight: 'ArrowRight'
  };
  if (names[ev.code]) return names[ev.code];
  return (ev.key || ev.code || '').length === 1 ? (ev.key || '').toUpperCase() : (ev.key || ev.code || '');
}

function formatShortcut(sc){
  if (!sc) return '未设置';
  var parts = [];
  if (sc.ctrlKey) parts.push(prettyModifier('ctrl'));
  if (sc.altKey) parts.push(prettyModifier('alt'));
  if (sc.shiftKey) parts.push(prettyModifier('shift'));
  if (sc.metaKey) parts.push(prettyModifier('meta'));
  parts.push(sc.key || sc.code || '');
  return parts.filter(Boolean).join(' + ');
}

function shortcutFromEvent(ev){
  if (['Control', 'Shift', 'Alt', 'Meta'].indexOf(ev.key) !== -1) return null;
  if (!(ev.ctrlKey || ev.altKey || ev.metaKey)) return null;
  var key = prettyKey(ev);
  return {
    code: ev.code,
    key: key,
    ctrlKey: !!ev.ctrlKey,
    altKey: !!ev.altKey,
    shiftKey: !!ev.shiftKey,
    metaKey: !!ev.metaKey
  };
}

function renderShortcut(sc){
  currentShortcut = sc || DEFAULT_SHORTCUT;
  if (!recordingShortcut) $('recordShortcut').textContent = formatShortcut(currentShortcut);
}

function setRecordingShortcut(on){
  recordingShortcut = !!on;
  $('recordShortcut').classList.toggle('recording', recordingShortcut);
  $('recordShortcut').textContent = recordingShortcut ? '按下快捷键' : formatShortcut(currentShortcut || DEFAULT_SHORTCUT);
}

$('recordShortcut').onclick = function(){
  setRecordingShortcut(!recordingShortcut);
};

document.addEventListener('keydown', function(ev){
  if (!recordingShortcut) return;
  ev.preventDefault();
  ev.stopPropagation();

  if (ev.key === 'Escape') {
    setRecordingShortcut(false);
    toast('已取消设置');
    return;
  }

  var shortcut = shortcutFromEvent(ev);
  if (!shortcut) {
    toast('请按带 ⌃ / ⌥ / ⌘ 的组合键');
    return;
  }

  chrome.storage.local.set(storageObj(K_SHORTCUT, shortcut), function(){
    renderShortcut(shortcut);
    setRecordingShortcut(false);
    toast('已保存标记快捷键');
  });
}, true);

/* ---- 确保 content script 已注入（失败则用 scripting 自动补注入，免刷新） ---- */
function ensureInjected(tabId, cb){
  tabMsg(tabId, { type:'ps-ping' }, function(resp){
    if (resp){ cb(resp); return; }
    if (!chrome.scripting){ cb(null); return; }
    chrome.scripting.insertCSS({ target:{ tabId:tabId, allFrames:true }, files:['content.css'] }).catch(function(){});
    chrome.scripting.executeScript({ target:{ tabId:tabId, allFrames:true }, files:['content.js'] }).then(function(){
      tabMsg(tabId, { type:'ps-ping' }, function(r2){ cb(r2 || null); });
    }, function(){ cb(null); });
  });
}

/* ---- 环境自检 ---- */
function addCheck(state, html, runId){
  if (runId !== checkRunId) return;
  var icon = state === 'ok' ? '✓' : (state === 'warn' ? '!' : '×');
  var div = document.createElement('div');
  div.className = 'chk';
  div.innerHTML = '<span class="ic '+state+'">'+icon+'</span><span class="tx">'+html+'</span>';
  $('checks').innerHTML = '';
  $('checks').appendChild(div);
}

function runChecks(){
  var runId = ++checkRunId;
  $('checks').innerHTML = '';

  var url = activeTab ? (activeTab.url || '') : '';

  if (isRestrictedUrl(url)){
    addCheck('no', '浏览器页面受限', runId);
    return;
  }
  if (!activeTab){
    addCheck('no', '浏览器页面受限', runId);
    return;
  }
  if (!isLocalUrl(url) && !allUrlsEnabled){
    addCheck('no', '浏览器页面受限', runId);
    return;
  }

  ensureInjected(activeTab.id, function(resp){
    if (resp && resp.active !== false){
      addCheck('ok', '标记器已就绪', runId);
    } else {
      addCheck('no', '浏览器页面受限', runId);
    }
  });
}

function isLocalUrl(url){
  try {
    var u = new URL(url || '');
    var host = (u.hostname || '').toLowerCase();
    return u.protocol === 'file:' ||
      host === 'localhost' ||
      host === '::1' ||
      host === '[::1]' ||
      host === '0.0.0.0' ||
      /^127(?:\.\d{1,3}){0,3}$/.test(host);
  } catch(e) {
    return false;
  }
}

function isRestrictedUrl(url){
  return /^(chrome|edge|about|chrome-extension|https:\/\/chrome\.google\.com\/webstore|https:\/\/chromewebstore\.google\.com)/.test(url || '');
}

function isCurrentPageAllowed(){
  var url = activeTab ? (activeTab.url || '') : '';
  return !!activeTab && !isRestrictedUrl(url) && (allUrlsEnabled || isLocalUrl(url));
}
