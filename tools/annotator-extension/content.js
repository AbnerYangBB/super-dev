/* ============================================================
 * PinSpec · content script
 * 通用网页/原型标记器：注入到任意页面与子框架，直接操作真实 DOM
 *   - 标记模式下悬停高亮、点击选中元素
 *   - 元素旁浮层输入备注
 *   - 已标记元素红框 + 编号图钉
 *   - 备注存 chrome.storage.local，按 URL 分组
 *   - 顶层框架渲染悬浮按钮与备注面板
 *   - 导出 JSON / Markdown / AI Prompt（配合 pinspec-annotations skill）
 * ============================================================ */
(function () {
  if (!window.chrome || !chrome.storage || !chrome.runtime) return;
  // 防重复注入：manifest 声明注入 + popup 手动补注入可能同时发生
  if (window.__pinspec_loaded) return;
  window.__pinspec_loaded = true;

  var SKILL = 'pinspec-annotations';
  var K_MODE = 'ps_mode', K_ANNS = 'ps_anns', K_FOCUS = 'ps_focus', K_CONTINUOUS = 'ps_continuous', K_FAB_POS = 'ps_fab_pos';
  var URLKEY = location.href.split('#')[0];
  var PAGE = (location.pathname.split('/').pop() || 'page').replace(/\.[a-z]+$/i, '') || 'page';
  var isTop = (window.top === window);

  var mode = false;
  var continuousMode = false;
  var fabPos = null;
  var anns = [];
  var hoverEl = null, pickedEl = null;
  var pins = [];           // {ann, el, pinEl}
  var rafPending = false;

  /* ---------------- 选择器工具 ---------------- */
  function cssEsc(s){ return (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/([^\w-])/g, '\\$1'); }
  function selectorFor(el){
    if (el.id) return '#' + cssEsc(el.id);
    var parts = [], node = el, depth = 0;
    while (node && node.nodeType === 1 && node !== document.body && node !== document.documentElement && depth < 6){
      if (node.id){ parts.unshift('#' + cssEsc(node.id)); break; }
      var seg = node.tagName.toLowerCase();
      var cls = Array.prototype.slice.call(node.classList || []).filter(function(c){ return c.indexOf('ps-') !== 0; });
      if (cls.length) seg += '.' + cls.slice(0,3).map(cssEsc).join('.');
      var p = node.parentElement;
      if (p){
        var same = Array.prototype.slice.call(p.children).filter(function(c){ return c.tagName === node.tagName; });
        if (same.length > 1) seg += ':nth-of-type(' + (same.indexOf(node) + 1) + ')';
      }
      parts.unshift(seg); node = p; depth++;
    }
    return parts.join(' > ');
  }
  function textFor(el){ var t = (el.textContent || '').trim().replace(/\s+/g, ' '); return t.length > 80 ? t.slice(0,80)+'…' : t; }
  function htmlFor(el){ var h = (el.outerHTML || '').replace(/\s+/g,' ').trim(); return h.length > 240 ? h.slice(0,240)+'…' : h; }
  // 先按选择器找，失败再按标签+文本兜底
  function findEl(a){
    var el = null;
    try { el = document.querySelector(a.selector); } catch(e){}
    if (el) return el;
    if (a.tag && a.target){
      var key = a.target.replace(/…$/,'');
      var list = document.getElementsByTagName(a.tag);
      for (var i=0;i<list.length;i++){ if ((list[i].textContent||'').trim().replace(/\s+/g,' ').indexOf(key) === 0) return list[i]; }
    }
    return null;
  }

  /* ---------------- 存储 ---------------- */
  function loadAll(cb){
    chrome.storage.local.get([K_MODE, K_ANNS, K_CONTINUOUS, K_FAB_POS], function(d){
      mode = !!d[K_MODE];
      continuousMode = !!d[K_CONTINUOUS];
      fabPos = d[K_FAB_POS] || null;
      anns = d[K_ANNS] || [];
      cb && cb();
    });
  }
  function persistAnns(){ var o = {}; o[K_ANNS] = anns; chrome.storage.local.set(o); }
  function setModeStore(on){ var o = {}; o[K_MODE] = !!on; chrome.storage.local.set(o); }
  function myAnns(){ return anns.filter(function(a){ return a.url === URLKEY; }); }

  /* ---------------- 跨页定位（通用，不依赖特定站点结构） ---------------- */
  function normUrl(u){ return (u || '').split('#')[0]; }
  function sameUrl(a, b){ return normUrl(a) === normUrl(b); }

  function pathPrefixScore(src, target){
    try {
      var s = new URL(src, location.href).pathname.split('/').filter(Boolean);
      var t = new URL(target, location.href).pathname.split('/').filter(Boolean);
      var n = 0;
      for (var i = 0; i < Math.min(s.length, t.length); i++){
        if (s[i] !== t[i]) break;
        n++;
      }
      return n;
    } catch(e){ return 0; }
  }

  // 从多个 iframe 中挑选最可能承载目标 URL 的一个（路径前缀 + 可见面积）
  function pickIframeForAnn(frames, url){
    if (!frames.length) return null;
    if (frames.length === 1) return frames[0];
    var best = null, bestScore = -1;
    for (var i = 0; i < frames.length; i++){
      var fr = frames[i];
      var src = fr.getAttribute('src') || '';
      var score = (!src || src === 'about:blank') ? 1 : (10 + pathPrefixScore(src, url));
      var r = fr.getBoundingClientRect();
      score += Math.min(5, Math.floor((r.width * r.height) / 20000));
      if (score > bestScore){ bestScore = score; best = fr; }
    }
    return best;
  }

  // 定位时尝试导航：已有 iframe 命中 → 换 src → 整页跳转（均基于 URL，无站点硬编码）
  function tryNavigateToAnn(a){
    if (!a || !a.url || !isTop) return false;
    if (sameUrl(a.url, URLKEY)) return true;

    var frames = document.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++){
      var src = frames[i].getAttribute('src') || frames[i].src || '';
      if (!src || src === 'about:blank') continue;
      try { if (sameUrl(new URL(src, location.href).href, a.url)) return true; } catch(e){}
    }

    var picked = pickIframeForAnn(frames, a.url);
    if (picked){
      picked.src = a.url;
      return true;
    }

    location.href = a.url;
    return true;
  }

  function focusAnn(a){
    if (!a) return;
    var el = findEl(a);
    if (el) flash(el);
  }

  function applyPendingFocus(){
    chrome.storage.local.get([K_FOCUS], function(d){
      var f = d[K_FOCUS];
      if (!f || !sameUrl(f.url, URLKEY)) return;
      var a = anns.filter(function(x){ return x.id === f.id; })[0];
      if (!a) return;
      setTimeout(function(){ focusAnn(a); }, 160);
    });
  }

  function requestFocus(a){
    if (!a) return;
    var o = {}; o[K_FOCUS] = { url: a.url, id: a.id, ts: Date.now() };
    chrome.storage.local.set(o);
    if (!sameUrl(a.url, URLKEY) && isTop) tryNavigateToAnn(a);
    else if (sameUrl(a.url, URLKEY)) focusAnn(a);
  }

  /* ---------------- 悬停高亮 ---------------- */
  function onOver(e){ if(!mode) return; if(isOurs(e.target)) return; if(hoverEl) hoverEl.classList.remove('ps-hover'); hoverEl = e.target; hoverEl.classList.add('ps-hover'); }
  function onOut(e){ if(!mode) return; if(e.target && e.target.classList) e.target.classList.remove('ps-hover'); }
  function isOurs(el){ return !!(el && el.closest && el.closest('.ps-root')); }

  /* ---------------- 点击选中 ---------------- */
  function onClick(e){
    if (!mode) return;
    if (isOurs(e.target)) return;          // 点到我们自己的 UI 不拦截
    e.preventDefault(); e.stopPropagation();
    clearPicked();
    pickedEl = e.target;
    pickedEl.classList.add('ps-picked');
    var r = pickedEl.getBoundingClientRect();
    openPopover({
      selector: selectorFor(pickedEl),
      tag: pickedEl.tagName.toLowerCase(),
      target: textFor(pickedEl),
      html: htmlFor(pickedEl)
    }, { left:r.left, top:r.top, right:r.right, bottom:r.bottom });
  }
  function clearPicked(){ if (pickedEl){ pickedEl.classList.remove('ps-picked'); pickedEl = null; } }

  /* ---------------- 备注输入浮层 ---------------- */
  var pop = null;
  function openPopover(ctx, anchor, existingAnn){
    closePopover();
    var isEdit = !!existingAnn;
    pop = document.createElement('div');
    pop.className = 'ps-root ps-pop';
    var meta = '&lt;' + ctx.tag + '&gt; ' + (ctx.target ? '“' + esc(ctx.target) + '”' : '') + '<br><code>' + esc(ctx.selector) + '</code>';
    var remote = isEdit && !sameUrl(existingAnn.url, URLKEY);
    if (remote){
      meta = '<div class="ps-pop-remote">所属页面：' + esc(existingAnn.page || '其他') + ' · 可直接改备注，无需跳转</div>' + meta;
    }
    pop.innerHTML =
      '<div class="ps-pop-h">' + (isEdit ? '编辑备注' : '标记元素') + '</div>' +
      '<div class="ps-pop-meta">' + meta + '</div>' +
      '<textarea class="ps-pop-ta" placeholder="写下要改的内容，例如：文案改成…、间距太大、删掉这张卡片…"></textarea>' +
      '<div class="ps-pop-act"><button class="ps-btn ghost" data-act="cancel">取消</button><button class="ps-btn primary" data-act="save">保存</button></div>';
    document.documentElement.appendChild(pop);
    place(pop, anchor);
    var ta = pop.querySelector('.ps-pop-ta');
    if (isEdit) ta.value = existingAnn.note || '';
    setTimeout(function(){ ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }, 20);
    pop.querySelector('[data-act="cancel"]').onclick = function(){ closePopover(); clearPicked(); };
    pop.querySelector('[data-act="save"]').onclick = function(){
      var note = ta.value.trim(); if (!note){ ta.focus(); return; }
      if (isEdit){
        for (var i = 0; i < anns.length; i++){
          if (anns[i].id === existingAnn.id){ anns[i].note = note; anns[i].ts = new Date().toISOString(); break; }
        }
      } else {
        anns.push({ id:'a'+Date.now()+Math.floor(Math.random()*1e4), url:URLKEY, page:PAGE, title:document.title||'', scope:'element', selector:ctx.selector||null, tag:ctx.tag||null, target:ctx.target||null, html:ctx.html||null, note:note, ts:new Date().toISOString() });
      }
      persistAnns(); closePopover(); clearPicked();
      if (!isEdit && !continuousMode) setModeStore(false);
    };
    ta.addEventListener('keydown', function(ev){ if((ev.metaKey||ev.ctrlKey) && ev.key==='Enter') pop.querySelector('[data-act="save"]').click(); if(ev.key==='Escape'){ closePopover(); clearPicked(); } });
  }
  function closePopover(){ if (pop){ pop.remove(); pop = null; } }
  function place(el, anchor){
    var pw = el.offsetWidth || 300, ph = el.offsetHeight || 220, gap = 10;
    var left, top;
    if (anchor){
      left = anchor.right + gap;
      if (left + pw > innerWidth - 8) left = anchor.left - pw - gap;
      if (left < 8) left = 8;
      top = anchor.top;
      if (top + ph > innerHeight - 8) top = innerHeight - ph - 8;
      if (top < 8) top = 8;
    } else { left = (innerWidth-pw)/2; top = 80; }
    el.style.left = left + 'px'; el.style.top = top + 'px';
  }

  /* ---------------- 标记可视化（红框 + 图钉） ---------------- */
  var pinLayer = null;
  function ensureLayer(){
    if (pinLayer && document.body && document.body.contains(pinLayer)) return pinLayer;
    pinLayer = document.createElement('div'); pinLayer.className = 'ps-root ps-pins';
    (document.body || document.documentElement).appendChild(pinLayer);
    return pinLayer;
  }
  function renderMarkers(){
    Array.prototype.slice.call(document.querySelectorAll('.ps-marked')).forEach(function(n){ n.classList.remove('ps-marked'); });
    ensureLayer().innerHTML = ''; pins = [];
    myAnns().forEach(function(a, i){
      if (a.scope !== 'element') return;
      var el = findEl(a); if (!el) return;
      el.classList.add('ps-marked');
      var pin = document.createElement('div'); pin.className = 'ps-pin'; pin.textContent = (i+1);
      pin.title = a.note;
      pin.addEventListener('click', function(ev){ ev.stopPropagation(); flash(el); });
      pinLayer.appendChild(pin);
      pins.push({ ann:a, el:el, pinEl:pin });
    });
    updatePins();
  }
  function updatePins(){
    pins.forEach(function(p){
      if (!document.body.contains(p.el)){ p.pinEl.style.display='none'; return; }
      var r = p.el.getBoundingClientRect();
      p.pinEl.style.display = '';
      p.pinEl.style.left = (r.left + scrollX - 6) + 'px';
      p.pinEl.style.top = (r.top + scrollY - 10) + 'px';
    });
  }
  function scheduleUpdate(){ if(rafPending) return; rafPending = true; requestAnimationFrame(function(){ rafPending=false; updatePins(); }); }
  function flash(el){ el.classList.add('ps-flash'); el.scrollIntoView({behavior:'smooth', block:'center'}); setTimeout(function(){ el.classList.remove('ps-flash'); }, 1400); }

  /* ---------------- 顶层：可拖动悬浮按钮 + 面板 ---------------- */
  var fab, panel;
  function applyFabPos(){
    if (!fab) return;
    if (fabPos && typeof fabPos.x === 'number' && typeof fabPos.y === 'number'){
      fab.style.left = fabPos.x + 'px';
      fab.style.top = fabPos.y + 'px';
      fab.style.right = 'auto';
      fab.style.bottom = 'auto';
    } else {
      fab.style.right = '18px';
      fab.style.bottom = '18px';
      fab.style.left = 'auto';
      fab.style.top = 'auto';
    }
  }
  function clampFabPos(x, y){
    var w = fab.offsetWidth || 52, h = fab.offsetHeight || 52, pad = 8;
    return {
      x: Math.max(pad, Math.min(x, innerWidth - w - pad)),
      y: Math.max(pad, Math.min(y, innerHeight - h - pad))
    };
  }
  function persistFabPos(pos){
    fabPos = pos;
    var o = {}; o[K_FAB_POS] = pos; chrome.storage.local.set(o);
  }
  function bindFabDrag(){
    var dragging = false, moved = false, startX = 0, startY = 0, originX = 0, originY = 0;
    fab.addEventListener('pointerdown', function(e){
      if (e.button !== 0) return;
      dragging = true; moved = false;
      startX = e.clientX; startY = e.clientY;
      var r = fab.getBoundingClientRect();
      originX = r.left; originY = r.top;
      fab.classList.add('dragging');
      fab.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    fab.addEventListener('pointermove', function(e){
      if (!dragging) return;
      var dx = e.clientX - startX, dy = e.clientY - startY;
      if (!moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      moved = true;
      var p = clampFabPos(originX + dx, originY + dy);
      fab.style.left = p.x + 'px'; fab.style.top = p.y + 'px';
      fab.style.right = 'auto'; fab.style.bottom = 'auto';
    });
    fab.addEventListener('pointerup', function(e){
      if (!dragging) return;
      dragging = false;
      fab.classList.remove('dragging');
      try { fab.releasePointerCapture(e.pointerId); } catch(err){}
      if (moved){
        var r = fab.getBoundingClientRect();
        persistFabPos(clampFabPos(r.left, r.top));
      } else {
        togglePanel();
      }
    });
    fab.addEventListener('pointercancel', function(){ dragging = false; fab.classList.remove('dragging'); });
  }
  function buildFab(){
    fab = document.createElement('div'); fab.className = 'ps-root ps-fab';
    fab.innerHTML = '<i class="ps-i">✎</i><span class="ps-fab-badge" style="display:none">0</span>';
    fab.title = 'PinSpec 标记（拖动可移动，点击打开面板）';
    document.documentElement.appendChild(fab);
    applyFabPos();
    bindFabDrag();
  }
  function buildPanel(){
    panel = document.createElement('div'); panel.className = 'ps-root ps-panel';
    panel.innerHTML =
      '<div class="ps-p-h"><b>PinSpec 标记</b><span class="ps-p-close">×</span></div>' +
      '<div class="ps-p-bar">' +
        '<label class="ps-switch"><input type="checkbox" class="ps-mode-cb"><span></span>标记模式</label>' +
      '</div>' +
      '<div class="ps-p-list"></div>' +
      '<div class="ps-p-foot">' +
        '<button class="ps-btn primary sm ps-exp-prompt" title="配合 ' + SKILL + ' skill 使用">导出为 Prompt</button>' +
        '<button class="ps-btn ghost sm ps-exp">JSON</button>' +
        '<button class="ps-btn ghost sm ps-exp-md">MD</button>' +
        '<button class="ps-btn ghost sm danger ps-clr">清空</button>' +
      '</div>';
    document.documentElement.appendChild(panel);
    panel.querySelector('.ps-p-close').onclick = function(){ panel.classList.remove('open'); };
    panel.querySelector('.ps-mode-cb').onchange = function(){ setModeStore(this.checked); };
    panel.querySelector('.ps-exp-prompt').onclick = function(){ copyText(buildPrompt(anns)); };
    panel.querySelector('.ps-exp').onclick = function(){ exportJSON(); };
    panel.querySelector('.ps-exp-md').onclick = function(){ exportMD(); };
    panel.querySelector('.ps-clr').onclick = function(){ if(confirm('清空全部备注？')){ anns = []; persistAnns(); } };
  }
  function togglePanel(){ panel.classList.toggle('open'); renderPanel(); }
  function renderPanel(){
    if (!isTop || !panel) return;
    panel.querySelector('.ps-mode-cb').checked = mode;
    var list = panel.querySelector('.ps-p-list');
    if (!anns.length){ list.innerHTML = '<div class="ps-empty">还没有备注。<br>开「标记模式」后点击页面元素即可添加。</div>'; return; }
    var byPage = {}; anns.forEach(function(a){ (byPage[a.page]=byPage[a.page]||[]).push(a); });
    var html = '';
    Object.keys(byPage).forEach(function(pg){
      html += '<div class="ps-grp"><div class="ps-grp-t">'+esc(pg)+' · '+byPage[pg].length+'</div>';
      byPage[pg].forEach(function(a){
        html += '<div class="ps-item" data-id="'+a.id+'" data-url="'+esc(a.url)+'">'+
          '<span class="ps-edit" data-id="'+a.id+'" title="编辑">✎</span>'+
          '<span class="ps-del" data-id="'+a.id+'" title="删除">×</span>'+
          (a.tag ? '<div class="ps-t">&lt;'+esc(a.tag)+'&gt; '+(a.target?esc(a.target):'')+'</div>' : '')+
          '<div class="ps-n">'+esc(a.note)+'</div></div>';
      });
      html += '</div>';
    });
    list.innerHTML = html;
    Array.prototype.slice.call(list.querySelectorAll('.ps-del')).forEach(function(b){
      b.onclick = function(e){
        e.stopPropagation();
        var id = b.getAttribute('data-id');
        anns = anns.filter(function(x){ return x.id !== id; });
        persistAnns();
      };
    });
    Array.prototype.slice.call(list.querySelectorAll('.ps-edit')).forEach(function(b){
      b.onclick = function(e){
        e.stopPropagation();
        var id = b.getAttribute('data-id');
        var a = anns.filter(function(x){ return x.id === id; })[0];
        if (!a) return;
        var onPage = sameUrl(a.url, URLKEY);
        var el = onPage ? findEl(a) : null;
        var anchor = el ? el.getBoundingClientRect() : null;
        openPopover({
          selector: a.selector || '',
          tag: a.tag || 'div',
          target: a.target || '',
          html: a.html || ''
        }, anchor, a);
      };
    });
    Array.prototype.slice.call(list.querySelectorAll('.ps-item')).forEach(function(it){
      it.onclick = function(e){
        if (e.target.closest('.ps-del') || e.target.closest('.ps-edit')) return;
        var id = it.getAttribute('data-id');
        var a = anns.filter(function(x){ return x.id === id; })[0];
        if (a) requestFocus(a);
      };
    });
  }
  function refreshFab(){
    if(!isTop||!fab) return;
    var b=fab.querySelector('.ps-fab-badge'); b.textContent=anns.length; b.style.display=anns.length?'flex':'none';
    fab.classList.toggle('on', mode);
    fab.style.display = 'flex';
  }

  /* ---------------- 导出 ---------------- */
  function payload(){ return { tool:'PinSpec', skill:SKILL, generatedAt:new Date().toISOString(), total:anns.length, annotations:anns }; }
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
  function download(name, text, type){
    var blob = new Blob([text], {type:type}); var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href=url; a.download=name; document.documentElement.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }
  function exportJSON(){ if(!anns.length){ toast('没有备注'); return; } download('annotations.json', JSON.stringify(payload(), null, 2), 'application/json'); toast('已导出 annotations.json'); }
  function exportMD(){
    if(!anns.length){ toast('没有备注'); return; }
    var byPage={}; anns.forEach(function(a){ (byPage[a.page]=byPage[a.page]||[]).push(a); });
    var md = '# 原型标记反馈\n\n';
    Object.keys(byPage).forEach(function(pg){ md += '## '+pg+'\n\n'; byPage[pg].forEach(function(a){ md += '- `'+(a.selector||'')+'` '+(a.target?('“'+a.target+'”'):'')+'\n  - 备注：'+a.note+'\n'; }); md += '\n'; });
    download('annotations.md', md, 'text/markdown');
    toast('已导出 annotations.md');
  }

  /* 复制到剪贴板（兼容非安全上下文） */
  function copyText(text){
    if (!anns.length){ toast('没有备注'); return; }
    var done = function(){ toast('Prompt 已复制，粘贴给 AI 即可'); };
    if (navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(done, function(){ fallbackCopy(text, done); });
    } else { fallbackCopy(text, done); }
  }
  function fallbackCopy(text, done){
    var ta = document.createElement('textarea'); ta.value = text; ta.style.position='fixed'; ta.style.opacity='0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch(e){ toast('复制失败，请改用导出 JSON'); }
    ta.remove();
  }

  /* 轻量 toast */
  var toastEl = null, toastTimer = null;
  function toast(m){
    if (!toastEl){ toastEl = document.createElement('div'); toastEl.className='ps-root ps-toast'; document.documentElement.appendChild(toastEl); }
    toastEl.textContent = m; toastEl.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(function(){ toastEl.classList.remove('show'); }, 1800);
  }

  /* ---------------- 模式应用 ---------------- */
  function applyMode(){
    document.documentElement.classList.toggle('ps-active', mode);
    if (!mode){ if(hoverEl){ hoverEl.classList.remove('ps-hover'); hoverEl=null; } clearPicked(); closePopover(); }
    refreshFab();
  }

  function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  /* ---------------- 事件绑定 ---------------- */
  document.addEventListener('mouseover', onOver, true);
  document.addEventListener('mouseout', onOut, true);
  document.addEventListener('click', onClick, true);
  window.addEventListener('scroll', scheduleUpdate, true);
  window.addEventListener('resize', function(){
    scheduleUpdate();
    if (isTop && fab && fabPos){
      var p = clampFabPos(fabPos.x, fabPos.y);
      if (p.x !== fabPos.x || p.y !== fabPos.y) persistFabPos(p);
      else applyFabPos();
    }
  });
  var mo = new MutationObserver(function(){ scheduleUpdate(); });

  /* ---------------- storage 同步 ---------------- */
  chrome.storage.onChanged.addListener(function(changes, area){
    if (area !== 'local') return;
    if (changes[K_MODE]){ mode = !!changes[K_MODE].newValue; applyMode(); }
    if (changes[K_CONTINUOUS]){ continuousMode = !!changes[K_CONTINUOUS].newValue; }
    if (changes[K_FAB_POS]){ fabPos = changes[K_FAB_POS].newValue || null; if(isTop) applyFabPos(); }
    if (changes[K_ANNS]){ anns = changes[K_ANNS].newValue || []; renderMarkers(); if(isTop){ renderPanel(); refreshFab(); } }
    if (changes[K_FOCUS] && changes[K_FOCUS].newValue){
      var f = changes[K_FOCUS].newValue;
      var a = anns.filter(function(x){ return x.id === f.id; })[0];
      if (!a) return;
      if (sameUrl(f.url, URLKEY)) focusAnn(a);
      else if (isTop) tryNavigateToAnn(a);
    }
  });

  /* ---------------- 来自 popup / background 的消息 ---------------- */
  chrome.runtime.onMessage.addListener(function(msg, sender, reply){
    if (!msg || !msg.type) return;
    if (msg.type === 'ps-ping'){
      reply({ ok:true, isTop:isTop, page:PAGE, url:URLKEY, total:anns.length, mine:myAnns().length, mode:mode });
      return true;
    }
    if (msg.type === 'ps-open-panel'){
      if (isTop && panel){ panel.classList.add('open'); renderPanel(); }
      reply({ ok: !!isTop });
      return true;
    }
    if (msg.type === 'ps-export-json'){
      exportJSON();
      reply({ ok: true });
      return true;
    }
  });

  /* ---------------- 启动 ---------------- */
  loadAll(function(){
    applyMode();
    renderMarkers();
    applyPendingFocus();
    try { mo.observe(document.documentElement, {childList:true, subtree:true}); } catch(e){}
    if (isTop){ buildFab(); buildPanel(); renderPanel(); refreshFab(); }
  });
})();
