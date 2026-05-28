'use strict';

// --- State ---
let pollTimer = null;
let currentView = 'search';

// --- API ---
async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const r = await fetch('/api' + path, opts);
  if (!r.ok) {
    let msg = `Error ${r.status}`;
    try { const d = await r.json(); msg = d.detail || msg; } catch {}
    throw new Error(msg);
  }
  const text = await r.text();
  return text ? JSON.parse(text) : null;
}

// --- Toast ---
let toastTimer = null;
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = 'toast hidden'; }, 4000);
}

// --- Formatting ---
function humanSize(bytes) {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let v = bytes;
  for (const u of units) {
    if (v < 1024) return v.toFixed(1) + ' ' + u;
    v /= 1024;
  }
  return v.toFixed(1) + ' PB';
}

function humanSpeed(bps) {
  if (!bps) return '—';
  return humanSize(bps) + '/s';
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function badgeClass(status) {
  const s = (status || '').toLowerCase();
  if (['completed', 'seeding', 'cached', 'uploading'].includes(s)) return 'badge-completed';
  if (['downloading', 'checkingfiles', 'forceddl'].includes(s)) return 'badge-downloading';
  if (['queued', 'pending', 'waiting', 'metadl', 'checkingresumedata', 'allocating', 'paused', 'stalleddl', 'stalledul'].includes(s)) return 'badge-queued';
  if (['error', 'failed', 'missingfiles'].includes(s)) return 'badge-failed';
  if (s === 'running') return 'badge-running';
  return 'badge-unknown';
}

// --- Navigation ---
function showView(name) {
  currentView = name;
  document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
  document.getElementById('view-' + name).classList.remove('hidden');
  document.querySelectorAll('.nav-link').forEach(el => {
    el.classList.toggle('active', el.dataset.view === name);
  });
  window.location.hash = name;

  if (name === 'dashboard') {
    loadTorrents();
    startPolling();
  } else {
    stopPolling();
  }
}

// --- Search ---
async function doSearch() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;

  const status = document.getElementById('search-status');
  const wrap = document.getElementById('search-results');
  const btn = document.getElementById('search-btn');

  status.innerHTML = '<span class="spinner"></span>Searching…';
  wrap.classList.add('hidden');
  btn.disabled = true;

  try {
    const results = await api('GET', '/search?q=' + encodeURIComponent(q));
    renderResults(results);
    status.textContent = results.length ? `${results.length} results` : 'No results found.';
    if (results.length) wrap.classList.remove('hidden');
  } catch (e) {
    status.textContent = '';
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

function renderResults(results) {
  const tbody = document.getElementById('results-body');
  if (!results.length) { tbody.innerHTML = ''; return; }

  tbody.innerHTML = results.map(r => {
    const canAdd = !!(r.magnet_url || r.download_url);
    return `<tr>
      <td class="title-cell" title="${esc(r.title)}">${esc(r.title)}</td>
      <td class="mono">${esc(r.size_human)}</td>
      <td class="mono" style="color:var(--green)">${r.seeders}</td>
      <td class="mono">${r.leechers}</td>
      <td class="mono">${esc(r.indexer)}</td>
      <td>
        <button class="btn-small ${canAdd ? '' : 'btn-secondary'}"
          onclick="addTorrent(${esc(JSON.stringify(r.magnet_url||null))}, ${esc(JSON.stringify(r.download_url||null))}, ${esc(JSON.stringify(r.title))})"
          ${canAdd ? '' : 'disabled'}>
          ${canAdd ? 'Add' : 'No link'}
        </button>
      </td>
    </tr>`;
  }).join('');
}

// --- Torrents ---
async function addTorrent(magnet, downloadUrl, title) {
  try {
    const body = magnet ? { magnet } : { download_url: downloadUrl, title };
    await api('POST', '/torrents', body);
    toast('Torrent added — switching to dashboard', 'success');
    showView('dashboard');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function loadTorrents() {
  const status = document.getElementById('dashboard-status');
  try {
    const [torrents, syncJobs] = await Promise.all([
      api('GET', '/torrents'),
      api('GET', '/sync/status'),
    ]);
    renderTorrents(torrents, syncJobs);
    status.textContent = `${torrents.length} torrent${torrents.length !== 1 ? 's' : ''}`;
  } catch (e) {
    status.textContent = '';
    toast(e.message, 'error');
  }
}

function renderTorrents(torrents, syncJobs) {
  const syncMap = {};
  for (const j of syncJobs) syncMap[j.torrent_id] = j;

  const tbody = document.getElementById('torrents-body');
  if (!torrents.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty">No torrents. Search and add one.</td></tr>';
    renderSyncJobs(syncJobs);
    return;
  }

  tbody.innerHTML = torrents.map(t => {
    const pct = Math.round((t.progress || 0) * 100);
    const done = t.download_finished || t.cached;
    const syncJob = syncMap[t.id];
    const syncDone = syncJob && syncJob.status === 'completed';
    const syncRunning = syncJob && syncJob.status === 'running';

    let syncBtn = '';
    if (done && !syncDone && !syncRunning) {
      syncBtn = `<button class="btn-small btn-sync" onclick="triggerSync(${t.id}, ${esc(JSON.stringify(t.name))})">Sync</button>`;
    } else if (syncRunning) {
      syncBtn = `<button class="btn-small btn-secondary" disabled><span class="spinner"></span>Syncing</button>`;
    } else if (syncDone) {
      syncBtn = `<span class="badge badge-completed">Synced</span>`;
    }

    return `<tr>
      <td class="title-cell" title="${esc(t.name)}">${esc(t.name)}</td>
      <td class="mono">${humanSize(t.size)}</td>
      <td>
        <div class="progress-wrap">
          <div class="progress-bar"><div class="progress-fill ${done ? 'done' : ''}" style="width:${pct}%"></div></div>
          <span class="progress-pct">${pct}%</span>
        </div>
      </td>
      <td class="mono">${humanSpeed(t.download_speed)}</td>
      <td><span class="badge ${badgeClass(t.status)}">${esc(t.status)}</span></td>
      <td>
        <div class="actions">
          ${syncBtn}
          <button class="btn-small btn-danger" onclick="deleteTorrent(${t.id}, ${esc(JSON.stringify(t.name))})">Delete</button>
        </div>
      </td>
    </tr>`;
  }).join('');

  renderSyncJobs(syncJobs);
}

async function deleteTorrent(id, name) {
  if (!confirm(`Delete "${name}" from TorBox?`)) return;
  try {
    await api('DELETE', `/torrents/${id}`);
    toast('Torrent deleted', 'success');
    loadTorrents();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// --- Sync ---
async function triggerSync(torrentId, torrentName) {
  try {
    await api('POST', `/sync/${torrentId}?torrent_name=${encodeURIComponent(torrentName)}`);
    toast(`Sync started for "${torrentName}"`, 'success');
    loadTorrents();
  } catch (e) {
    toast(e.message, 'error');
  }
}

function renderSyncJobs(jobs) {
  const tbody = document.getElementById('sync-body');
  if (!jobs.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">No sync jobs yet.</td></tr>';
    return;
  }
  tbody.innerHTML = jobs.map(j => `<tr>
    <td class="title-cell" title="${esc(j.torrent_name)}">${esc(j.torrent_name)}</td>
    <td><span class="badge ${badgeClass(j.status)}">${esc(j.status)}</span></td>
    <td class="mono">${fmtDate(j.started_at)}</td>
    <td class="mono">${fmtDate(j.finished_at)}</td>
    <td class="mono" style="color:var(--red);max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${esc(j.error || '')}">${esc(j.error || '')}</td>
  </tr>`).join('');
}

// --- Polling ---
function startPolling() {
  stopPolling();
  pollTimer = setInterval(loadTorrents, 10000);
}

function stopPolling() {
  clearInterval(pollTimer);
  pollTimer = null;
}

// --- Utils ---
function esc(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  // Nav clicks
  document.querySelectorAll('.nav-link').forEach(el => {
    el.addEventListener('click', e => { e.preventDefault(); showView(el.dataset.view); });
  });

  // Search
  document.getElementById('search-btn').addEventListener('click', doSearch);
  document.getElementById('search-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') doSearch();
  });

  // Refresh button
  document.getElementById('refresh-btn').addEventListener('click', loadTorrents);

  // Route from hash
  const hash = window.location.hash.replace('#', '');
  showView(['search', 'dashboard'].includes(hash) ? hash : 'search');
});
