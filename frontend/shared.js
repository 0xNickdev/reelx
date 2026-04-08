const API_URL = 'https://reelx-production.up.railway.app';

// REELX SHARED JS
document.addEventListener('DOMContentLoaded', function() {
  // Scroll reveal
  var obs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) { if (e.isIntersecting) e.target.classList.add('in'); });
  }, { threshold: 0.07 });
  document.querySelectorAll('.reveal').forEach(function(el) { obs.observe(el); });

  // FAQ accordion
  document.querySelectorAll('.faq-q').forEach(function(q) {
    q.addEventListener('click', function() {
      var item = q.parentElement;
      var isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(function(i) { i.classList.remove('open'); });
      if (!isOpen) item.classList.add('open');
    });
  });

  // Filter buttons
  document.querySelectorAll('.filter-group').forEach(function(group) {
    group.querySelectorAll('.f-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        group.querySelectorAll('.f-btn').forEach(function(b) { b.classList.remove('on'); });
        btn.classList.add('on');
      });
    });
  });

  // Toggle buttons
  document.querySelectorAll('.toggle-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { btn.classList.toggle('on'); });
  });
});

// ─── AUTH HELPERS ───────────────────────────────────────
function getCurrentUserId() { return localStorage.getItem('reelx_user_id'); }
function getCurrentToken() { return localStorage.getItem('reelx_token'); }
function isLoggedIn() { return !!localStorage.getItem('reelx_user_id'); }


function getAuthHeaders() {
  var token = getCurrentToken();
  var headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  return headers;
}

function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

// ─── API CALLS ──────────────────────────────────────────
async function apiRegister(name, email, password) {
  var res = await fetch(API_URL + '/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, email: email, password: password })
  });
  var data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Ошибка регистрации');
  return data;
}

async function apiLogin(email, password) {
  var res = await fetch(API_URL + '/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, password: password })
  });
  var data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Неверный email или пароль');
  localStorage.setItem('reelx_user_id', data.user_id);
  localStorage.setItem('reelx_token', data.access_token);
  localStorage.setItem('reelx_email', data.email);
  return data;
}

function apiLogout() {
  localStorage.removeItem('reelx_user_id');
  localStorage.removeItem('reelx_token');
  localStorage.removeItem('reelx_email');
  window.location.href = 'index.html';
}

async function apiStartAnalysis(url) {
  var userId = getCurrentUserId();
  if (!userId) { window.location.href = 'login.html'; return; }
  var res = await fetch(API_URL + '/api/analyze/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: url, user_id: userId })
  });
  var data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Ошибка запуска анализа');
  return data;
}

async function apiGetJobStatus(jobId) {
  var res = await fetch(API_URL + '/api/analyze/status/' + jobId, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Job not found');
  return res.json();
}

function pollJob(jobId, onProgress, onDone, onError) {
  var timer = setInterval(async function() {
    try {
      var data = await apiGetJobStatus(jobId);
      onProgress(data);
      if (data.status === 'done') { clearInterval(timer); onDone(data); }
      else if (data.status === 'failed') { clearInterval(timer); onError(data.error || 'Ошибка'); }
    } catch(e) { clearInterval(timer); onError(e.message); }
  }, 2000);
  return timer;
}

async function apiGetHistory() {
  var userId = getCurrentUserId();
  var res = await fetch(API_URL + '/api/analyze/history/' + userId, {
    headers: getAuthHeaders()
  });
  return res.json();
}

async function apiGetSubscription() {
  var userId = getCurrentUserId();
  var res = await fetch(API_URL + '/api/payments/subscription/' + userId, {
    headers: getAuthHeaders()
  });
  return res.json();
}

async function apiGetSettings() {
  var userId = getCurrentUserId();
  var res = await fetch(API_URL + '/api/settings/' + userId, {
    headers: getAuthHeaders()
  });
  return res.json();
}

async function apiSaveSettings(settings) {
  var userId = getCurrentUserId();
  var res = await fetch(API_URL + '/api/settings/update', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.assign({ user_id: userId }, settings))
  });
  if (!res.ok) throw new Error('Ошибка сохранения');
  return res.json();
}

async function apiGetTrends(niche, platform, sort) {
  var params = new URLSearchParams({
    niche: niche || 'all',
    platform: platform || 'all',
    sort: sort || 'xfactor',
    limit: '20'
  });
  var res = await fetch(API_URL + '/api/trends/feed?' + params);
  return res.json();
}

// ─── UTILS ──────────────────────────────────────────────
function copyText(elId) {
  var el = document.getElementById(elId);
  if (!el) return;
  var text = el.innerText || el.textContent;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(function() { showToast('Скопировано ✓'); });
  } else {
    var ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    showToast('Скопировано ✓');
  }
}

function showToast(msg, type) {
  var t = document.createElement('div');
  t.textContent = msg;
  var bg = type === 'error' ? '#f87171' : '#e8ddd2';
  var color = type === 'error' ? '#fff' : '#0c0c0e';
  t.style.cssText = 'position:fixed;bottom:28px;left:50%;transform:translateX(-50%);background:' + bg + ';color:' + color + ';padding:10px 22px;border-radius:8px;font-size:0.82rem;font-weight:600;z-index:9999;font-family:inherit;pointer-events:none;';
  document.body.appendChild(t);
  setTimeout(function() { t.style.opacity='0'; t.style.transition='opacity 0.3s'; setTimeout(function(){t.remove();},300); }, 2500);
}

function goPage(url) { window.location.href = url; }

function formatNumber(n) {
  if (!n) return '0';
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'М';
  if (n >= 1000) return (n/1000).toFixed(1) + 'К';
  return String(n);
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  var diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (diff < 3600) return Math.floor(diff/60) + ' мин. назад';
  if (diff < 86400) return Math.floor(diff/3600) + ' ч. назад';
  return Math.floor(diff/86400) + ' дн. назад';
}
