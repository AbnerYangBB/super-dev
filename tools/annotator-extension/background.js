/* ============================================================
 * PinSpec · service worker
 * 角标显示备注数
 * ============================================================ */
var K_ANNS = 'ps_anns';

function refreshBadge() {
  chrome.storage.local.get([K_ANNS], function (d) {
    var n = (d[K_ANNS] || []).length;
    chrome.action.setBadgeText({ text: n ? String(n) : '' });
    chrome.action.setBadgeBackgroundColor({ color: '#A78BFA' });
  });
}

chrome.runtime.onInstalled.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);
chrome.storage.onChanged.addListener(function (changes, area) {
  if (area === 'local' && changes[K_ANNS]) refreshBadge();
});
