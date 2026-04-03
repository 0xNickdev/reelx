/**
 * REELX Frontend API Client
 * Add this file to your frontend project as api.js
 * Import it in shared.js or each page that needs API calls
 */

const API_URL = 'https://reelx-backend-production.up.railway.app'; // Update after deploy

// ─── AUTH ───────────────────────────────────────────
async function apiRegister(name, email, password) {
  const res = await fetch(`${API_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || 'Ошибка регистрации');
  return res.json();
}

async function apiLogin(email, password) {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || 'Неверные данные');
  const data = await res.json();
  // Save to localStorage
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

function getCurrentUserId() {
  return localStorage.getItem('reelx_user_id');
}

function isLoggedIn() {
  return !!localStorage.getItem('reelx_user_id');
}

// ─── ANALYZE ────────────────────────────────────────
async function apiStartAnalysis(url) {
  const userId = getCurrentUserId();
  if (!userId) throw new Error('Не авторизован');

  const res = await fetch(`${API_URL}/api/analyze/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, user_id: userId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Ошибка запуска анализа');
  }
  return res.json(); // { job_id, status }
}

async function apiGetJobStatus(jobId) {
  const res = await fetch(`${API_URL}/api/analyze/status/${jobId}`);
  if (!res.ok) throw new Error('Job not found');
  return res.json();
}

// Poll job status until done or failed
function pollJobStatus(jobId, onProgress, onDone, onError, intervalMs = 2000) {
  const timer = setInterval(async () => {
    try {
      const data = await apiGetJobStatus(jobId);
      onProgress(data);
      if (data.status === 'done' || data.status === 'failed') {
        clearInterval(timer);
        if (data.status === 'done') onDone(data);
        else onError(data.error || 'Ошибка анализа');
      }
    } catch (e) {
      clearInterval(timer);
      onError(e.message);
    }
  }, intervalMs);
  return timer;
}

async function apiGetHistory() {
  const userId = getCurrentUserId();
  const res = await fetch(`${API_URL}/api/analyze/history/${userId}`);
  return res.json();
}

// ─── SETTINGS ───────────────────────────────────────
async function apiGetSettings() {
  const userId = getCurrentUserId();
  const res = await fetch(`${API_URL}/api/settings/${userId}`);
  return res.json();
}

async function apiSaveSettings(settings) {
  const userId = getCurrentUserId();
  const res = await fetch(`${API_URL}/api/settings/update`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, ...settings }),
  });
  if (!res.ok) throw new Error('Ошибка сохранения');
  return res.json();
}

// ─── PAYMENTS ───────────────────────────────────────
async function apiCreatePayment(method) {
  const userId = getCurrentUserId();
  const res = await fetch(`${API_URL}/api/payments/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, method }),
  });
  if (!res.ok) throw new Error('Ошибка создания платежа');
  return res.json();
}

async function apiGetSubscription() {
  const userId = getCurrentUserId();
  const res = await fetch(`${API_URL}/api/payments/subscription/${userId}`);
  return res.json();
}

// ─── TRENDS ─────────────────────────────────────────
async function apiGetTrends(niche = 'all', platform = 'all', sort = 'xfactor') {
  const params = new URLSearchParams({ niche, platform, sort, limit: '20' });
  const res = await fetch(`${API_URL}/api/trends/feed?${params}`);
  return res.json();
}

// Export for use in pages
if (typeof module !== 'undefined') {
  module.exports = { apiRegister, apiLogin, apiLogout, apiStartAnalysis, apiGetJobStatus, pollJobStatus, apiGetHistory, apiGetSettings, apiSaveSettings, apiCreatePayment, apiGetSubscription, apiGetTrends, getCurrentUserId, isLoggedIn };
}
