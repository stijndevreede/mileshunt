// XP Hunt — Frontend logic v5 (2026-03-30)

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let groups = [];
let activeGroups = new Set();
let expandedGroup = null;
let userToken = localStorage.getItem('xphunt_token');
let currentUser = null;
let searchAbort = null;
let allDeals = []; // accumulated deals during search

// ── Init ───────────────────────────────────────────────────

async function init() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfter = new Date();
  dayAfter.setDate(dayAfter.getDate() + 2);
  $('#date').value = tomorrow.toISOString().split('T')[0];
  $('#return-date').value = dayAfter.toISOString().split('T')[0];

  try {
    const resp = await fetch('/api/groups');
    groups = await resp.json();
    renderGroupChips();
  } catch (e) {
    console.error('Failed to load groups:', e);
  }

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

  $('#login-submit').addEventListener('click', doLogin);
  $('#login-password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  $('#login-close').addEventListener('click', closeLoginModal);
  $('#logout-btn').addEventListener('click', doLogout);

  onTripTypeChange();

  // Validate stored token on load
  if (userToken) {
    try {
      const r = await fetch(`/api/me?token=${userToken}`);
      if (r.ok) {
        currentUser = await r.json();
      } else {
        clearAuth();
      }
    } catch (e) {
      clearAuth();
    }
  }
  updateAuthUI();
}

// ── Auth ───────────────────────────────────────────────────

function clearAuth() {
  localStorage.removeItem('xphunt_token');
  userToken = null;
  currentUser = null;
}

function updateAuthUI() {
  if (currentUser) {
    $('#user-info').hidden = false;
    $('#user-name').textContent = currentUser.name;
    if ($('#best-deals-link')) $('#best-deals-link').hidden = false;
  } else {
    $('#user-info').hidden = true;
    if ($('#best-deals-link')) $('#best-deals-link').hidden = true;
  }
}

function requireAuth() {
  // Returns true if logged in, false if login modal was shown
  if (userToken && currentUser) return true;
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
  if (searchAbort) {
    searchAbort.abort();
    searchAbort = null;
  }
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
  if (userToken) {
    fetch(`/api/logout?token=${userToken}`, { method: 'POST' }).catch(() => {});
  }
  clearAuth();
  updateAuthUI();
  resetSearchUI();
}

function onTripTypeChange() {
  const isReturn = $('#trip-type').value === 'return';
  $('#return-field').style.display = isReturn ? '' : 'none';
}

// ── Leaderboard ────────────────────────────────────────────


// ── Group Chips ────────────────────────────────────────────

function renderGroupChips() {
  const container = $('#group-chips');
  container.innerHTML = '';

  for (const g of groups) {
    const chip = document.createElement('button');
    chip.className = 'chip' + (g.default_on ? ' active' : '');
    chip.textContent = g.label;
    chip.title = g.description + ' (' + g.destinations.length + ' destinations)';
    chip.dataset.id = g.id;

    if (g.default_on) activeGroups.add(g.id);

    chip.addEventListener('click', (e) => {
      if (e.shiftKey) { toggleGroupDetail(g, chip); return; }
      chip.classList.toggle('active');
      if (activeGroups.has(g.id)) activeGroups.delete(g.id);
      else activeGroups.add(g.id);
    });

    chip.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      toggleGroupDetail(g, chip);
    });

    container.appendChild(chip);
  }
}

function toggleGroupDetail(group, chipEl) {
  const detail = $('#group-detail');
  $$('.chip.expanded').forEach(c => c.classList.remove('expanded'));

  if (expandedGroup === group.id) {
    detail.hidden = true;
    expandedGroup = null;
    return;
  }

  expandedGroup = group.id;
  chipEl.classList.add('expanded');

  const names = group.destination_names || {};
  const tags = group.destinations.map(code => {
    const name = names[code] || code;
    return `<span class="dest-tag"><span class="dest-code">${code}</span> ${name}</span>`;
  }).join('');

  detail.innerHTML = `
    <div class="group-detail-title">${group.label}</div>
    <div class="group-detail-desc">${group.description}</div>
    <div class="dest-list">${tags}</div>
  `;
  detail.hidden = false;
}

// ── Hunt with SSE Progress ─────────────────────────────────

async function runHunt() {
  const origin = $('#origin').value.trim().toUpperCase() || 'AMS';
  const date = $('#date').value;
  const cabin = $('#cabin').value;
  const isReturn = $('#trip-type').value === 'return';
  const returnDate = isReturn ? $('#return-date').value : null;

  if (!date) { showStatus('Please select an outbound date.', false); return; }
  if (isReturn && !returnDate) { showStatus('Please select a return date.', false); return; }
  if (activeGroups.size === 0) { showStatus('Select at least one destination group.', false); return; }

  // Auth gate: check in-memory first, then verify with server
  if (!requireAuth()) return;

  const btn = $('#btn-hunt');
  btn.disabled = true;
  btn.textContent = 'Searching...';
  showStatus('Connecting to Google Flights...', true);
  $('#stats').hidden = true;
  $('#results').innerHTML = '';

  // Create abort controller for this search
  cancelSearch();
  searchAbort = new AbortController();
  const signal = searchAbort.signal;

  try {
    const body = { origin, date, cabin, groups: [...activeGroups] };
    if (returnDate) body.return_date = returnDate;

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
            // Add new deals incrementally
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
              $('#results').innerHTML = `
                <div class="empty">
                  <h3>No XP-earning flights found</h3>
                  <p>Try different dates or enable more destination groups.</p>
                </div>`;
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
    if (e.name === 'AbortError') return; // cancelled, no error
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

function hideStatus() {
  $('#status').hidden = true;
}

// ── Render Results ─────────────────────────────────────────

function updateStats(deals) {
  if (!deals || deals.length === 0) {
    $('#stats').hidden = true;
    return;
  }
  const statsBar = $('#stats');
  statsBar.hidden = false;
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

  deals.forEach((deal, i) => {
    container.appendChild(createCard(deal, i + 1));
  });
}

function fmtDuration(mins) {
  if (!mins) return '';
  return `${Math.floor(mins / 60)}h${String(mins % 60).padStart(2, '0')}m`;
}

function renderBreakdown(segments, label) {
  if (!segments || segments.length === 0) return '';
  let html = `<div class="breakdown-label">${label}</div>`;
  html += segments.map(seg => {
    const fbNote = seg.earns_fb ? '' : '<span class="seg-no-fb">no FB</span>';
    return `<div class="seg">
      <span class="seg-route">${seg.from} &gt; ${seg.to}</span>
      <span class="seg-airline">${seg.airline}</span>
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
  // Google Flights cabin: 1=economy, 2=premium eco, 3=business, 4=first
  const cabinNum = { economy: 1, premium: 2, business: 3, first: 4 }[cabin] || 3;
  const tripType = isRT ? 1 : 2; // 1=round trip, 2=one way

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

  let breakdownHTML = renderBreakdown(deal.xp_breakdown, 'Outbound');
  if (isRT && deal.return_xp_breakdown && deal.return_xp_breakdown.length > 0) {
    breakdownHTML += renderBreakdown(deal.return_xp_breakdown, 'Return');
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
      <div class="metric">
        <div class="metric-value price">\u20AC${Math.round(deal.price).toLocaleString()}</div>
        <div class="metric-label">Price</div>
      </div>
      <div class="metric">
        <div class="metric-value xp">${deal.xp_total}</div>
        <div class="metric-label">${xpLabel}</div>
      </div>
      <div class="metric">
        <div class="metric-value per-xp">\u20AC${deal.per_xp}</div>
        <div class="metric-label">\u20AC/XP</div>
      </div>
      <div class="metric">
        <div class="metric-value price">${segLabel}</div>
        <div class="metric-label">Segments</div>
      </div>
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
