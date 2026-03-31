// XP Hunt — Frontend logic v15 (2026-03-31)

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let categories = [];        // [{id, label, icon, items}]
let selectedGroups = new Set();
let customCodes = new Set(); // individual IATA codes
let userToken = localStorage.getItem('xphunt_token');
let currentUser = JSON.parse(localStorage.getItem('xphunt_user') || 'null');
let searchAbort = null;
let allDeals = [];
let activeTab = 'continents';

// ── Init ───────────────────────────────────────────────────

async function init() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfter = new Date();
  dayAfter.setDate(dayAfter.getDate() + 2);
  $('#date').value = tomorrow.toISOString().split('T')[0];
  $('#return-date').value = dayAfter.toISOString().split('T')[0];

  // Load destination categories
  try {
    const resp = await fetch('/api/destinations');
    categories = await resp.json();
  } catch (e) {
    console.error('Failed to load destinations:', e);
  }

  // Wire events
  $('#btn-hunt').addEventListener('click', runHunt);
  $('#trip-type').addEventListener('change', onTripTypeChange);
  $('#xp-ref-toggle').addEventListener('click', () => {
    $('#xp-ref').hidden = !$('#xp-ref').hidden;
    $('#tips-panel').hidden = true;
  });
  $('#tips-toggle').addEventListener('click', () => {
    $('#tips-panel').hidden = !$('#tips-panel').hidden;
    $('#xp-ref').hidden = true;
  });

  // Login
  $('#login-submit').addEventListener('click', doLogin);
  $('#login-password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  $('#login-close').addEventListener('click', closeLoginModal);
  $('#logout-btn').addEventListener('click', doLogout);

  // Destination picker
  $('#btn-destinations').addEventListener('click', openDestPicker);
  $('#dest-modal-close').addEventListener('click', closeDestPicker);
  $('#dest-done').addEventListener('click', closeDestPicker);
  $('#dest-clear').addEventListener('click', () => {
    selectedGroups.clear();
    customCodes.clear();
    renderDestPicker();
    renderCustomIataTags();
    updateDestUI();
  });
  $('#dest-search').addEventListener('input', renderDestPicker);
  $$('.dest-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      activeTab = tab.dataset.tab;
      $$('.dest-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === activeTab));
      switchDestTab();
    });
  });

  // Custom IATA
  $('#custom-iata-add').addEventListener('click', addCustomIata);
  $('#custom-iata-input').addEventListener('keydown', e => { if (e.key === 'Enter') addCustomIata(); });

  onTripTypeChange();

  // Restore login state from localStorage
  console.log('[auth] init: token=', !!userToken, 'user=', currentUser?.name || 'null');

  // If we have token but no user object (old login before persistence was added), verify
  if (userToken && !currentUser?.name) {
    try {
      const r = await fetch(`/api/me?token=${userToken}`);
      if (r.ok) {
        currentUser = await r.json();
        localStorage.setItem('xphunt_user', JSON.stringify(currentUser));
        console.log('[auth] verified token, user=', currentUser.name);
      } else {
        console.log('[auth] token invalid, clearing');
        clearAuth();
      }
    } catch (e) {
      console.log('[auth] verify failed (network), keeping token');
    }
  }

  updateAuthUI();
  updateDestUI();
}

// ── Auth ───────────────────────────────────────────────────

function clearAuth() {
  localStorage.removeItem('xphunt_token');
  localStorage.removeItem('xphunt_user');
  userToken = null;
  currentUser = null;
}

function updateAuthUI() {
  if (currentUser && currentUser.name) {
    $('#user-info').hidden = false;
    $('#user-name').textContent = currentUser.name;
    if ($('#best-deals-link')) $('#best-deals-link').hidden = false;
  } else {
    $('#user-info').hidden = true;
    if ($('#best-deals-link')) $('#best-deals-link').hidden = true;
  }
}

function requireAuth() {
  if (userToken && currentUser && currentUser.name) return true;
  // Token exists but no user object — clear stale state
  if (userToken && !currentUser) clearAuth();
  showLoginModal();
  return false;
}

function showLoginModal() {
  cancelSearch();
  resetSearchUI();
  openLoginModal();
  $('#login-error').hidden = true;
  $('#login-email').value = '';
  $('#login-password').value = '';
  setTimeout(() => $('#login-email').focus(), 50);
}

function closeLoginModal() {
  const modal = $('#login-modal');
  modal.hidden = true;
  modal.style.display = 'none';
}

function openLoginModal() {
  const modal = $('#login-modal');
  modal.hidden = false;
  modal.style.display = '';
}

function cancelSearch() {
  if (searchAbort) { searchAbort.abort(); searchAbort = null; }
}

function resetSearchUI() {
  hideStatus();
  $('#stats').hidden = true;
  $('#results').innerHTML = '';
  const btn = $('#btn-hunt');
  btn.disabled = false;
  btn.textContent = 'Hunt XP';
}

async function doLogin() {
  const email = $('#login-email').value.trim();
  const password = $('#login-password').value;
  if (!email || !password) return;
  $('#login-submit').disabled = true;
  $('#login-submit').textContent = 'Logging in...';
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
    closeLoginModal();
    updateAuthUI();
  } catch (e) {
    $('#login-error').textContent = 'Connection error';
    $('#login-error').hidden = false;
  } finally {
    $('#login-submit').disabled = false;
    $('#login-submit').textContent = 'Login';
  }
}

async function doLogout() {
  cancelSearch();
  if (userToken) fetch(`/api/logout?token=${userToken}`, { method: 'POST' }).catch(() => {});
  clearAuth();
  updateAuthUI();
  resetSearchUI();
}

function onTripTypeChange() {
  const isReturn = $('#trip-type').value === 'return';
  $('#return-field').style.display = isReturn ? '' : 'none';
}

// ── Destination Picker ─────────────────────────────────────

function openDestPicker() {
  $('#dest-modal').hidden = false;
  $('#dest-modal').style.display = '';
  $('#dest-search').value = '';
  switchDestTab();
}

function closeDestPicker() {
  $('#dest-modal').hidden = true;
  $('#dest-modal').style.display = 'none';
  updateDestUI();
}

function switchDestTab() {
  const isCustom = activeTab === 'custom';
  $('#dest-search-row').hidden = isCustom;
  $('#dest-items').hidden = isCustom;
  $('#dest-custom').hidden = !isCustom;
  if (isCustom) {
    renderCustomIataTags();
    setTimeout(() => $('#custom-iata-input').focus(), 50);
  } else {
    renderDestPicker();
  }
  updateDestModalCount();
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
  container.innerHTML = [...customCodes].map(code => {
    const name = getAllCityNames()[code] || '';
    const nameSpan = name ? `<span class="tag-name">${name}</span>` : '';
    return `<span class="dest-custom-tag">${code} ${nameSpan}<span class="tag-x" data-code="${code}">&times;</span></span>`;
  }).join('');

  container.querySelectorAll('.tag-x').forEach(el => {
    el.addEventListener('click', () => {
      customCodes.delete(el.dataset.code);
      renderCustomIataTags();
      updateDestModalCount();
    });
  });
}

function getAllCityNames() {
  // Build a flat lookup from all category items
  const names = {};
  for (const cat of categories) {
    for (const item of cat.items) {
      if (item.destination_names) Object.assign(names, item.destination_names);
    }
  }
  return names;
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
      (item.tags || []).some(t => t.toLowerCase().includes(query)) ||
      item.destinations.some(d => d.toLowerCase().includes(query)) ||
      Object.values(item.destination_names || {}).some(n => n.toLowerCase().includes(query))
    );
  }

  container.innerHTML = items.map(item => {
    const checked = selectedGroups.has(item.id);
    return `<div class="dest-item ${checked ? 'selected' : ''}" data-id="${item.id}">
      <div class="dest-item-check">${checked ? '&#10003;' : ''}</div>
      <div class="dest-item-info">
        <div class="dest-item-label">${item.label}</div>
        <div class="dest-item-desc">${item.description}</div>
      </div>
      <div class="dest-item-count">${item.count} cities</div>
    </div>`;
  }).join('');

  // Click handlers
  container.querySelectorAll('.dest-item').forEach(el => {
    el.addEventListener('click', () => {
      const id = el.dataset.id;
      if (selectedGroups.has(id)) selectedGroups.delete(id);
      else selectedGroups.add(id);
      renderDestPicker();
      updateDestModalCount();
    });
  });

  updateDestModalCount();
}

function updateDestModalCount() {
  const totalDests = getSelectedDestCount();
  $('#dest-modal-count').textContent = `${totalDests} destinations selected`;
}

function getSelectedDestCount() {
  const allItems = categories.flatMap(c => c.items);
  const seen = new Set();
  for (const id of selectedGroups) {
    const item = allItems.find(i => i.id === id);
    if (item) item.destinations.forEach(d => seen.add(d));
  }
  customCodes.forEach(c => seen.add(c));
  return seen.size;
}

function updateDestUI() {
  const count = getSelectedDestCount();
  $('#dest-count').textContent = count;

  const tagsContainer = $('#dest-selected-tags');
  const allItems = categories.flatMap(c => c.items);

  // Group tags
  let html = '';
  for (const id of selectedGroups) {
    const item = allItems.find(i => i.id === id);
    if (item) html += `<span class="dest-sel-tag">${item.label} <span class="dest-sel-x" data-id="${id}">&times;</span></span>`;
  }
  // Custom IATA tags
  for (const code of customCodes) {
    html += `<span class="dest-sel-tag">${code} <span class="dest-sel-x dest-sel-custom" data-code="${code}">&times;</span></span>`;
  }
  tagsContainer.innerHTML = html;

  // Remove group tag click
  tagsContainer.querySelectorAll('.dest-sel-x:not(.dest-sel-custom)').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      selectedGroups.delete(el.dataset.id);
      updateDestUI();
    });
  });
  // Remove custom code tag click
  tagsContainer.querySelectorAll('.dest-sel-custom').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      customCodes.delete(el.dataset.code);
      updateDestUI();
    });
  });
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
  if (selectedGroups.size === 0 && customCodes.size === 0) {
    showStatus('Select destinations first (click the Destinations button).', false);
    return;
  }
  if (!requireAuth()) return;

  const btn = $('#btn-hunt');
  btn.disabled = true;
  btn.textContent = 'Searching...';
  showStatus('Connecting to Google Flights...', true);
  $('#stats').hidden = true;
  $('#results').innerHTML = '';

  cancelSearch();
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
      updateAuthUI();
      showLoginModal();
      return;
    }

    if (!resp.ok) {
      showStatus(`Error: ${await resp.text()}`, false);
      return;
    }

    allDeals = [];
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let searchDone = false;

    while (!searchDone) {
      if (signal.aborted) break;
      const readPromise = reader.read();
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('stream_timeout')), 30000)
      );
      let done, value;
      try {
        ({ done, value } = await Promise.race([readPromise, timeoutPromise]));
      } catch (e) {
        if (e.message === 'stream_timeout') break;
        throw e;
      }
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'progress') {
            if (data.new_deals && data.new_deals.length > 0) {
              allDeals.push(...data.new_deals);
              allDeals.sort((a, b) => a.per_xp - b.per_xp);
              renderResults(allDeals);
            }
            showProgress(data.current, data.total, data.route, data.flights_found);
          } else if (data.type === 'done') {
            hideStatus();
            allDeals.sort((a, b) => a.per_xp - b.per_xp);
            if (allDeals.length === 0) {
              $('#results').innerHTML = `<div class="empty"><h3>No XP-earning flights found</h3><p>Try different dates or destinations.</p></div>`;
            } else {
              renderResults(allDeals);
            }
            updateStats(allDeals);
            searchDone = true;
            break;
          }
        } catch (e) {}
      }
    }
    reader.cancel().catch(() => {});
  } catch (e) {
    if (e.name === 'AbortError') return;
    showStatus(`Network error: ${e.message}`, false);
  } finally {
    searchAbort = null;
    btn.disabled = false;
    btn.textContent = 'Hunt XP';
  }
}

// ── Status ─────────────────────────────────────────────────

function showStatus(msg, loading) {
  const el = $('#status');
  el.hidden = false;
  el.innerHTML = (loading ? '<div class="spinner"></div>' : '') + `<span>${msg}</span>`;
}

function showProgress(current, total, route, flightsFound) {
  const pct = Math.round((current / total) * 100);
  const el = $('#status');
  el.hidden = false;
  el.innerHTML = `
    <div class="spinner"></div>
    <div class="progress-info">
      <div class="progress-text">${route}</div>
      <div class="progress-bar-wrap">
        <div class="progress-bar" style="width:${pct}%"></div>
      </div>
      <div class="progress-meta">${current} / ${total} destinations &middot; ${flightsFound} flights found</div>
    </div>
  `;
}

function hideStatus() { $('#status').hidden = true; }

// ── Render Results ─────────────────────────────────────────

function updateStats(deals) {
  if (!deals || deals.length === 0) { $('#stats').hidden = true; return; }
  $('#stats').hidden = false;
  $('#stat-routes').textContent = deals.length;
  $('#stat-best').textContent = `\u20AC${deals[0].per_xp}`;
  $('#stat-multi').textContent = deals.filter(d => d.total_segments >= 4).length;
  $('#stat-excellent').textContent = deals.filter(d => d.rating === 'EXCELLENT').length;
}

function renderResults(deals) {
  const container = $('#results');
  container.innerHTML = '';
  if (!deals || deals.length === 0) return;
  updateStats(deals);
  deals.forEach((deal, i) => container.appendChild(createCard(deal, i + 1)));
}

function fmtDuration(mins) {
  if (!mins) return '';
  return `${Math.floor(mins / 60)}h${String(mins % 60).padStart(2, '0')}m`;
}

function renderBreakdown(segments, legs, label) {
  if (!segments || segments.length === 0) return '';
  let html = `<div class="breakdown-label">${label}</div>`;
  html += segments.map((seg, i) => {
    const fbNote = seg.earns_fb ? '' : '<span class="seg-no-fb">no FB</span>';
    const leg = legs && legs[i];
    const aircraft = leg?.aircraft;
    const acIcon = aircraft ? `<span class="seg-aircraft" title="${aircraft}">&#9992;</span>` : '';
    return `<div class="seg">
      <span class="seg-route">${seg.from} &gt; ${seg.to}</span>
      <span class="seg-airline">${seg.airline}</span>
      ${acIcon}
      <span class="seg-xp">${seg.xp} XP</span>
      <span class="seg-band">${seg.band}</span>
      ${fbNote}
    </div>`;
  }).join('');
  return html;
}

function buildGoogleFlightsUrl(deal) {
  const origin = deal.origin;
  const dest = deal.dest;
  const date = deal.legs?.[0]?.departure?.split('T')[0] || '';
  const retDate = deal.return_legs?.[0]?.departure?.split('T')[0] || '';
  const isRT = deal.trip_type === 'return';
  const cabin = $('#cabin').value;
  const cabinNum = { economy: 1, premium: 2, business: 3, first: 4 }[cabin] || 3;
  const tripType = isRT ? 1 : 2;
  let url = `https://www.google.com/travel/flights?q=Flights+to+${dest}+from+${origin}`;
  if (date) url += `+on+${date}`;
  if (isRT && retDate) url += `+return+${retDate}`;
  url += `&curr=EUR&seat=${cabinNum}&trip=${tripType}`;
  return url;
}

function createCard(deal, rank) {
  const card = document.createElement('div');
  const ratingClass = deal.rating.toLowerCase();
  card.className = `card card-border-${ratingClass}`;

  const airlineStr = deal.airline_names.join(', ');
  const fbBadge = deal.all_fb
    ? '<span class="fb-badge fb-yes">All FB</span>'
    : '<span class="fb-badge fb-no">Mixed</span>';
  const isRT = deal.trip_type === 'return';
  const tripBadge = isRT ? '<span class="card-trip-badge">RT</span>' : '<span class="card-trip-badge">OW</span>';

  let breakdownHTML = renderBreakdown(deal.xp_breakdown, deal.legs, 'Outbound');
  if (isRT && deal.return_xp_breakdown && deal.return_xp_breakdown.length > 0) {
    breakdownHTML += renderBreakdown(deal.return_xp_breakdown, deal.return_legs, 'Return');
  }

  const returnRouteHTML = isRT && deal.return_route
    ? `<div class="card-return-route">&larr; ${deal.return_route}</div>` : '';
  const durStr = isRT
    ? `${fmtDuration(deal.duration)} + ${fmtDuration(deal.return_duration)}`
    : fmtDuration(deal.duration);
  const xpLabel = isRT ? 'XP (total)' : 'XP';
  const segLabel = isRT ? `${deal.outbound_segments}+${deal.return_segments} seg` : `${deal.total_segments} seg`;

  card.innerHTML = `
    <div class="card-top">
      <span class="card-rank">#${rank} ${tripBadge}</span>
      <span class="card-rating rating-${ratingClass}">${deal.rating}</span>
    </div>
    <div class="card-route">&rarr; ${deal.route}</div>
    ${returnRouteHTML}
    <div class="card-metrics">
      <div class="metric"><div class="metric-value price">\u20AC${Math.round(deal.price).toLocaleString()}</div><div class="metric-label">Price</div></div>
      <div class="metric"><div class="metric-value xp">${deal.xp_total}</div><div class="metric-label">${xpLabel}</div></div>
      <div class="metric"><div class="metric-value per-xp">\u20AC${deal.per_xp}</div><div class="metric-label">\u20AC/XP</div></div>
      <div class="metric"><div class="metric-value price">${segLabel}</div><div class="metric-label">Segments</div></div>
    </div>
    <div class="card-breakdown">${breakdownHTML}</div>
    <div class="card-footer">
      <span class="card-airlines-text">${airlineStr} ${fbBadge} &middot; ${durStr}</span>
      <a href="${buildGoogleFlightsUrl(deal)}" target="_blank" rel="noopener" class="btn-flights">Google Flights &rarr;</a>
    </div>
  `;
  return card;
}

// ── Boot ───────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
