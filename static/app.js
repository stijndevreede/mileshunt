// XP Hunt — Frontend v16

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

let categories = [];
let selectedGroups = new Set();
let customCodes = new Set();
let userToken = localStorage.getItem('xphunt_token');
let currentUser = null;
let searchAbort = null;
let allDeals = [];
let activeTab = 'continents';

// ── Boot ───────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);

async function init() {
  // Try restore session
  try { currentUser = JSON.parse(localStorage.getItem('xphunt_user')); } catch(e) {}

  if (userToken && currentUser && currentUser.name) {
    showApp();
  } else if (userToken) {
    // Have token but no user — verify once
    try {
      const r = await fetch(`/api/me?token=${userToken}`);
      if (r.ok) {
        currentUser = await r.json();
        localStorage.setItem('xphunt_user', JSON.stringify(currentUser));
        showApp();
      } else {
        clearAuth();
        showLogin();
      }
    } catch(e) {
      showLogin();
    }
  } else {
    showLogin();
  }
}

// ── Page switching ─────────────────────────────────────────

function showLogin() {
  $('#page-login').hidden = false;
  $('#page-app').hidden = true;
  wireLogin();
}

function showApp() {
  $('#page-login').hidden = true;
  $('#page-app').hidden = false;
  $('#user-name').textContent = currentUser?.name || '';
  wireApp();
}

function clearAuth() {
  localStorage.removeItem('xphunt_token');
  localStorage.removeItem('xphunt_user');
  userToken = null;
  currentUser = null;
}

// ── Login ──────────────────────────────────────────────────

let loginWired = false;
function wireLogin() {
  if (loginWired) return;
  loginWired = true;
  $('#login-submit').addEventListener('click', doLogin);
  $('#login-password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  $('#login-email').addEventListener('keydown', e => { if (e.key === 'Enter') $('#login-password').focus(); });
}

async function doLogin() {
  const email = $('#login-email').value.trim();
  const password = $('#login-password').value;
  if (!email || !password) return;

  const btn = $('#login-submit');
  btn.disabled = true;
  btn.textContent = 'Logging in...';
  $('#login-error').hidden = true;

  try {
    const r = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) {
      $('#login-error').textContent = 'Invalid email or password';
      $('#login-error').hidden = false;
      return;
    }
    const data = await r.json();
    userToken = data.token;
    currentUser = data.user;
    localStorage.setItem('xphunt_token', userToken);
    localStorage.setItem('xphunt_user', JSON.stringify(currentUser));
    showApp();
  } catch(e) {
    $('#login-error').textContent = 'Connection error';
    $('#login-error').hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Login';
  }
}

// ── App wiring ─────────────────────────────────────────────

let appWired = false;
async function wireApp() {
  if (appWired) return;
  appWired = true;

  // Dates
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfter = new Date(); dayAfter.setDate(dayAfter.getDate() + 2);
  $('#date').value = tomorrow.toISOString().split('T')[0];
  $('#return-date').value = dayAfter.toISOString().split('T')[0];

  // Load destinations
  try {
    const resp = await fetch('/api/destinations');
    categories = await resp.json();
  } catch(e) {}

  // Events
  $('#btn-hunt').addEventListener('click', runHunt);
  $('#trip-type').addEventListener('change', onTripTypeChange);
  $('#xp-ref-toggle').addEventListener('click', () => { $('#xp-ref').hidden = !$('#xp-ref').hidden; $('#tips-panel').hidden = true; });
  $('#tips-toggle').addEventListener('click', () => { $('#tips-panel').hidden = !$('#tips-panel').hidden; $('#xp-ref').hidden = true; });
  $('#logout-btn').addEventListener('click', () => {
    if (userToken) fetch(`/api/logout?token=${userToken}`, { method: 'POST' }).catch(() => {});
    clearAuth();
    location.reload();
  });

  // Destination picker
  $('#btn-destinations').addEventListener('click', openDestPicker);
  $('#dest-modal-close').addEventListener('click', closeDestPicker);
  $('#dest-done').addEventListener('click', closeDestPicker);
  $('#dest-clear').addEventListener('click', () => { selectedGroups.clear(); customCodes.clear(); renderDestPicker(); renderCustomIataTags(); updateDestUI(); });
  $('#dest-search').addEventListener('input', renderDestPicker);
  $$('.dest-tab').forEach(tab => tab.addEventListener('click', () => {
    activeTab = tab.dataset.tab;
    $$('.dest-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === activeTab));
    switchDestTab();
  }));
  $('#custom-iata-add').addEventListener('click', addCustomIata);
  $('#custom-iata-input').addEventListener('keydown', e => { if (e.key === 'Enter') addCustomIata(); });

  onTripTypeChange();
  updateDestUI();
}

function onTripTypeChange() {
  $('#return-field').style.display = $('#trip-type').value === 'return' ? '' : 'none';
}

// ── Destination Picker ─────────────────────────────────────

function openDestPicker() {
  $('#dest-modal').hidden = false;
  $('#dest-search').value = '';
  switchDestTab();
}

function closeDestPicker() {
  $('#dest-modal').hidden = true;
  updateDestUI();
}

function switchDestTab() {
  const isCustom = activeTab === 'custom';
  $('#dest-search-row').hidden = isCustom;
  $('#dest-items').hidden = isCustom;
  $('#dest-custom').hidden = !isCustom;
  if (isCustom) { renderCustomIataTags(); setTimeout(() => $('#custom-iata-input').focus(), 50); }
  else renderDestPicker();
  updateDestModalCount();
}

function renderDestPicker() {
  const container = $('#dest-items');
  const query = ($('#dest-search').value || '').toLowerCase().trim();
  const cat = categories.find(c => c.id === activeTab);
  if (!cat) { container.innerHTML = ''; return; }

  let items = cat.items;
  if (query) {
    items = items.filter(item =>
      item.label.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query) ||
      (item.tags || []).some(t => t.includes(query)) ||
      item.destinations.some(d => d.toLowerCase().includes(query)) ||
      Object.values(item.destination_names || {}).some(n => n.toLowerCase().includes(query))
    );
  }

  container.innerHTML = items.map(item => {
    const checked = selectedGroups.has(item.id);
    return `<div class="dest-item ${checked ? 'selected' : ''}" data-id="${item.id}">
      <div class="dest-item-check">${checked ? '&#10003;' : ''}</div>
      <div class="dest-item-info"><div class="dest-item-label">${item.label}</div><div class="dest-item-desc">${item.description}</div></div>
      <div class="dest-item-count">${item.count} cities</div>
    </div>`;
  }).join('');

  container.querySelectorAll('.dest-item').forEach(el => el.addEventListener('click', () => {
    const id = el.dataset.id;
    if (selectedGroups.has(id)) selectedGroups.delete(id); else selectedGroups.add(id);
    renderDestPicker();
    updateDestModalCount();
  }));
  updateDestModalCount();
}

function updateDestModalCount() {
  $('#dest-modal-count').textContent = `${getDestCount()} destinations selected`;
}

function getDestCount() {
  const seen = new Set();
  const allItems = categories.flatMap(c => c.items);
  for (const id of selectedGroups) {
    const item = allItems.find(i => i.id === id);
    if (item) item.destinations.forEach(d => seen.add(d));
  }
  customCodes.forEach(c => seen.add(c));
  return seen.size;
}

function addCustomIata() {
  const input = $('#custom-iata-input');
  const code = input.value.trim().toUpperCase();
  if (code.length === 3 && /^[A-Z]{3}$/.test(code)) {
    customCodes.add(code);
    input.value = '';
    renderCustomIataTags();
    updateDestModalCount();
  }
  input.focus();
}

function renderCustomIataTags() {
  const container = $('#custom-iata-tags');
  if (!container) return;
  if (customCodes.size === 0) {
    container.innerHTML = '<span style="color:var(--text-dim);font-size:12px">No custom destinations added yet.</span>';
    return;
  }
  const names = {};
  categories.forEach(c => c.items.forEach(i => { if (i.destination_names) Object.assign(names, i.destination_names); }));

  container.innerHTML = [...customCodes].map(code => {
    const name = names[code] || '';
    return `<span class="dest-custom-tag">${code}${name ? ` <span class="tag-name">${name}</span>` : ''}<span class="tag-x" data-code="${code}">&times;</span></span>`;
  }).join('');

  container.querySelectorAll('.tag-x').forEach(el => el.addEventListener('click', () => {
    customCodes.delete(el.dataset.code);
    renderCustomIataTags();
    updateDestModalCount();
  }));
}

function updateDestUI() {
  $('#dest-count').textContent = getDestCount();
  const container = $('#dest-selected-tags');
  const allItems = categories.flatMap(c => c.items);
  let html = '';
  for (const id of selectedGroups) {
    const item = allItems.find(i => i.id === id);
    if (item) html += `<span class="dest-sel-tag">${item.label} <span class="dest-sel-x" data-id="${id}">&times;</span></span>`;
  }
  for (const code of customCodes) {
    html += `<span class="dest-sel-tag">${code} <span class="dest-sel-x dest-sel-custom" data-code="${code}">&times;</span></span>`;
  }
  container.innerHTML = html;
  container.querySelectorAll('.dest-sel-x:not(.dest-sel-custom)').forEach(el => el.addEventListener('click', e => { e.stopPropagation(); selectedGroups.delete(el.dataset.id); updateDestUI(); }));
  container.querySelectorAll('.dest-sel-custom').forEach(el => el.addEventListener('click', e => { e.stopPropagation(); customCodes.delete(el.dataset.code); updateDestUI(); }));
}

// ── Hunt ───────────────────────────────────────────────────

async function runHunt() {
  const origin = $('#origin').value.trim().toUpperCase() || 'AMS';
  const date = $('#date').value;
  const cabin = $('#cabin').value;
  const isReturn = $('#trip-type').value === 'return';
  const returnDate = isReturn ? $('#return-date').value : null;

  if (!date) { showStatus('Please select an outbound date.', false); return; }
  if (isReturn && !returnDate) { showStatus('Please select a return date.', false); return; }
  if (selectedGroups.size === 0 && customCodes.size === 0) { showStatus('Select destinations first.', false); return; }

  const btn = $('#btn-hunt');
  btn.disabled = true;
  btn.textContent = 'Searching...';
  showStatus('Connecting to Google Flights...', true);
  $('#stats').hidden = true;
  $('#results').innerHTML = '';

  if (searchAbort) searchAbort.abort();
  searchAbort = new AbortController();
  const signal = searchAbort.signal;

  try {
    const body = { origin, date, cabin, groups: [...selectedGroups] };
    if (returnDate) body.return_date = returnDate;
    if (customCodes.size > 0) body.custom_codes = [...customCodes];

    const resp = await fetch(`/api/hunt/stream?token=${userToken}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });

    if (resp.status === 401) {
      clearAuth();
      location.reload();
      return;
    }
    if (!resp.ok) { showStatus(`Error: ${await resp.text()}`, false); return; }

    allDeals = [];
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let done = false;

    while (!done) {
      if (signal.aborted) break;
      let chunk;
      try {
        const readP = reader.read();
        const timeoutP = new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 30000));
        chunk = await Promise.race([readP, timeoutP]);
      } catch(e) { break; }
      if (chunk.done) break;

      buffer += decoder.decode(chunk.value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'progress') {
            if (data.new_deals?.length > 0) {
              allDeals.push(...data.new_deals);
              allDeals.sort((a, b) => a.per_xp - b.per_xp);
              renderResults(allDeals);
            }
            showProgress(data.current, data.total, data.route, data.flights_found);
          } else if (data.type === 'done') {
            hideStatus();
            allDeals.sort((a, b) => a.per_xp - b.per_xp);
            if (allDeals.length === 0) $('#results').innerHTML = '<div class="empty"><h3>No XP-earning flights found</h3><p>Try different dates or destinations.</p></div>';
            else renderResults(allDeals);
            updateStats(allDeals);
            done = true; break;
          }
        } catch(e) {}
      }
    }
    reader.cancel().catch(() => {});
  } catch(e) {
    if (e.name !== 'AbortError') showStatus(`Error: ${e.message}`, false);
  } finally {
    searchAbort = null;
    btn.disabled = false;
    btn.textContent = 'Hunt XP';
  }
}

// ── UI helpers ─────────────────────────────────────────────

function showStatus(msg, loading) { const el = $('#status'); el.hidden = false; el.innerHTML = (loading ? '<div class="spinner"></div>' : '') + `<span>${msg}</span>`; }
function showProgress(cur, total, route, found) {
  const pct = Math.round((cur / total) * 100);
  $('#status').hidden = false;
  $('#status').innerHTML = `<div class="spinner"></div><div class="progress-info"><div class="progress-text">${route}</div><div class="progress-bar-wrap"><div class="progress-bar" style="width:${pct}%"></div></div><div class="progress-meta">${cur} / ${total} destinations &middot; ${found} flights found</div></div>`;
}
function hideStatus() { $('#status').hidden = true; }

function updateStats(deals) {
  if (!deals?.length) { $('#stats').hidden = true; return; }
  $('#stats').hidden = false;
  $('#stat-routes').textContent = deals.length;
  $('#stat-best').textContent = `\u20AC${deals[0].per_xp}`;
  $('#stat-multi').textContent = deals.filter(d => d.total_segments >= 4).length;
  $('#stat-excellent').textContent = deals.filter(d => d.rating === 'EXCELLENT').length;
}

function renderResults(deals) {
  const c = $('#results'); c.innerHTML = '';
  if (!deals?.length) return;
  updateStats(deals);
  deals.forEach((d, i) => c.appendChild(createCard(d, i + 1)));
}

function fmtDur(m) { return m ? `${Math.floor(m/60)}h${String(m%60).padStart(2,'0')}m` : ''; }

function renderBreakdown(segs, legs, label) {
  if (!segs?.length) return '';
  return `<div class="breakdown-label">${label}</div>` + segs.map((s, i) => {
    const ac = legs?.[i]?.aircraft;
    return `<div class="seg"><span class="seg-route">${s.from} &gt; ${s.to}</span><span class="seg-airline">${s.airline}</span>${ac ? `<span class="seg-aircraft" title="${ac}">&#9992;</span>` : ''}<span class="seg-xp">${s.xp} XP</span><span class="seg-band">${s.band}</span>${s.earns_fb ? '' : '<span class="seg-no-fb">no FB</span>'}</div>`;
  }).join('');
}

function gfUrl(d) {
  const cabin = $('#cabin').value;
  const cn = {economy:1,premium:2,business:3,first:4}[cabin]||3;
  const dt = d.legs?.[0]?.departure?.split('T')[0]||'';
  const rd = d.return_legs?.[0]?.departure?.split('T')[0]||'';
  const rt = d.trip_type==='return';
  let u = `https://www.google.com/travel/flights?q=Flights+to+${d.dest}+from+${d.origin}`;
  if (dt) u += `+on+${dt}`;
  if (rt && rd) u += `+return+${rd}`;
  return u + `&curr=EUR&seat=${cn}&trip=${rt?1:2}`;
}

function createCard(d, rank) {
  const card = document.createElement('div');
  const rc = d.rating.toLowerCase();
  card.className = `card card-border-${rc}`;
  const rt = d.trip_type === 'return';
  const airlines = d.airline_names.join(', ');
  const fb = d.all_fb ? '<span class="fb-badge fb-yes">All FB</span>' : '<span class="fb-badge fb-no">Mixed</span>';
  const trip = rt ? '<span class="card-trip-badge">RT</span>' : '<span class="card-trip-badge">OW</span>';
  let bd = renderBreakdown(d.xp_breakdown, d.legs, 'Outbound');
  if (rt && d.return_xp_breakdown?.length) bd += renderBreakdown(d.return_xp_breakdown, d.return_legs, 'Return');
  const retRoute = rt && d.return_route ? `<div class="card-return-route">&larr; ${d.return_route}</div>` : '';
  const dur = rt ? `${fmtDur(d.duration)} + ${fmtDur(d.return_duration)}` : fmtDur(d.duration);
  const segs = rt ? `${d.outbound_segments}+${d.return_segments} seg` : `${d.total_segments} seg`;

  card.innerHTML = `
    <div class="card-top"><span class="card-rank">#${rank} ${trip}</span><span class="card-rating rating-${rc}">${d.rating}</span></div>
    <div class="card-route">&rarr; ${d.route}</div>${retRoute}
    <div class="card-metrics">
      <div class="metric"><div class="metric-value price">\u20AC${Math.round(d.price).toLocaleString()}</div><div class="metric-label">Price</div></div>
      <div class="metric"><div class="metric-value xp">${d.xp_total}</div><div class="metric-label">${rt?'XP (total)':'XP'}</div></div>
      <div class="metric"><div class="metric-value per-xp">\u20AC${d.per_xp}</div><div class="metric-label">\u20AC/XP</div></div>
      <div class="metric"><div class="metric-value price">${segs}</div><div class="metric-label">Segments</div></div>
    </div>
    <div class="card-breakdown">${bd}</div>
    <div class="card-footer"><span class="card-airlines-text">${airlines} ${fb} &middot; ${dur}</span><a href="${gfUrl(d)}" target="_blank" rel="noopener" class="btn-flights">Google Flights &rarr;</a></div>
  `;
  return card;
}
