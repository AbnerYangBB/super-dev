/* ============================================================
 * PinSpec · service worker
 * 快捷键切换标记模式 + 角标显示备注数
 * ============================================================ */
var K_MODE = 'ps_mode', K_ANNS = 'ps_anns';

// 快捷键 Alt+Shift+M 切换标记模式
chrome.commands.onCommand.addListener(function (cmd) {
  if (cmd !== 'toggle-mode') return;
  chrome.storage.local.get([K_MODE], function (d) {
    var o = {}; o[K_MODE] = !d[K_MODE]; chrome.storage.local.set(o);
  });
});

// 角标：展示全部备注数量
function refreshBadge() {
  chrome.storage.local.get([K_ANNS], function (d) {
    var n = (d[K_ANNS] || []).length;
    chrome.action.setBadgeText({ text: n ? String(n) : '' });
    chrome.action.setBadgeBackgroundColor({ color: '#F2685F' });
  });
}
chrome.runtime.onInstalled.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);
chrome.storage.onChanged.addListener(function (changes, area) {
  if (area === 'local' && changes[K_ANNS]) refreshBadge();
});
