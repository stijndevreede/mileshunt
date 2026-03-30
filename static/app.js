// XP Hunt — Frontend logic

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let groups = [];
let activeGroups = new Set();
let expandedGroup = null;

// ── Init ───────────────────────────────────────────────────

async function init() {
  // Set default dates: tomorrow + day after
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfter = new Date();
  dayAfter.setDate(dayAfter.getDate() + 2);
  $('#date').value = tomorrow.toISOString().split('T')[0];
  $('#return-date').value = dayAfter.toISOString().split('T')[0];

  // Load destination groups
  try {
    const resp = await fetch('/api/groups');
    groups = await resp.json();
    renderGroupChips();
  } catch (e) {
    console.error('Failed to load groups:', e);
  }

  // Wire up events
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

  onTripTypeChange();
}

function onTripTypeChange() {
  const isReturn = $('#trip-type').value === 'return';
  $('#return-field').style.display = isReturn ? '' : 'none';
}

// ── Group Chips with Expand ────────────────────────────────

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

    // Left click: toggle active
    chip.addEventListener('click', (e) => {
      if (e.shiftKey) {
        // Shift+click: expand/collapse detail
        toggleGroupDetail(g, chip);
        return;
      }
      chip.classList.toggle('active');
      if (activeGroups.has(g.id)) {
        activeGroups.delete(g.id);
      } else {
        activeGroups.add(g.id);
      }
    });

    // Right click: show detail
    chip.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      toggleGroupDetail(g, chip);
    });

    container.appendChild(chip);
  }
}

function toggleGroupDetail(group, chipEl) {
  const detail = $('#group-detail');

  // Remove expanded class from all chips
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

// ── Hunt ───────────────────────────────────────────────────

async function runHunt() {
  const origin = $('#origin').value.trim().toUpperCase() || 'AMS';
  const date = $('#date').value;
  const cabin = $('#cabin').value;
  const isReturn = $('#trip-type').value === 'return';
  const returnDate = isReturn ? $('#return-date').value : null;

  if (!date) {
    showStatus('Please select an outbound date.', false);
    return;
  }
  if (isReturn && !returnDate) {
    showStatus('Please select a return date.', false);
    return;
  }
  if (activeGroups.size === 0) {
    showStatus('Select at least one destination group.', false);
    return;
  }

  const btn = $('#btn-hunt');
  btn.disabled = true;
  btn.textContent = 'Searching...';

  showStatus('Searching Google Flights — this may take a minute...', true);
  $('#stats').hidden = true;
  $('#results').innerHTML = '';

  try {
    const body = { origin, date, cabin, groups: [...activeGroups] };
    if (returnDate) body.return_date = returnDate;

    const resp = await fetch('/api/hunt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.text();
      showStatus(`Error: ${err}`, false);
      return;
    }

    const data = await resp.json();
    hideStatus();
    renderResults(data.deals);
  } catch (e) {
    showStatus(`Network error: ${e.message}`, false);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Hunt XP';
  }
}

// ── Status ─────────────────────────────────────────────────

function showStatus(msg, loading) {
  const el = $('#status');
  el.hidden = false;
  el.innerHTML = (loading ? '<div class="spinner"></div>' : '') + msg;
}

function hideStatus() {
  $('#status').hidden = true;
}

// ── Render Results ─────────────────────────────────────────

function renderResults(deals) {
  const container = $('#results');
  container.innerHTML = '';

  if (!deals || deals.length === 0) {
    container.innerHTML = `
      <div class="empty">
        <h3>No XP-earning flights found</h3>
        <p>Try different dates or enable more destination groups.</p>
      </div>`;
    return;
  }

  // Stats
  const statsBar = $('#stats');
  statsBar.hidden = false;
  $('#stat-routes').textContent = deals.length;
  $('#stat-best').textContent = `$${deals[0].per_xp}`;
  $('#stat-multi').textContent = deals.filter(d => d.total_segments >= 4).length;
  $('#stat-excellent').textContent = deals.filter(d => d.rating === 'EXCELLENT').length;

  // Cards
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

function createCard(deal, rank) {
  const card = document.createElement('div');
  const ratingClass = deal.rating.toLowerCase();
  card.className = `card card-border-${ratingClass}`;

  const airlineStr = deal.airline_names.join(', ');
  const fbBadge = deal.all_fb
    ? '<span class="fb-badge fb-yes">All FB</span>'
    : '<span class="fb-badge fb-no">Mixed</span>';

  const isRT = deal.trip_type === 'return';
  const tripBadge = isRT
    ? '<span class="card-trip-badge">RT</span>'
    : '<span class="card-trip-badge">OW</span>';

  // Breakdown
  let breakdownHTML = renderBreakdown(deal.xp_breakdown, 'Outbound');
  if (isRT && deal.return_xp_breakdown && deal.return_xp_breakdown.length > 0) {
    breakdownHTML += renderBreakdown(deal.return_xp_breakdown, 'Return');
  }

  // Return route line
  const returnRouteHTML = isRT && deal.return_route
    ? `<div class="card-return-route">&larr; ${deal.return_route}</div>`
    : '';

  // Duration string
  const durStr = isRT
    ? `${fmtDuration(deal.duration)} + ${fmtDuration(deal.return_duration)}`
    : fmtDuration(deal.duration);

  // Metrics: for RT show total XP, for OW show one-way
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
        <div class="metric-value price">$${Math.round(deal.price).toLocaleString()}</div>
        <div class="metric-label">Price</div>
      </div>
      <div class="metric">
        <div class="metric-value xp">${deal.xp_total}</div>
        <div class="metric-label">${xpLabel}</div>
      </div>
      <div class="metric">
        <div class="metric-value per-xp">$${deal.per_xp}</div>
        <div class="metric-label">$/XP</div>
      </div>
      <div class="metric">
        <div class="metric-value price">${segLabel}</div>
        <div class="metric-label">Segments</div>
      </div>
    </div>
    <div class="card-breakdown">${breakdownHTML}</div>
    <div class="card-airlines">${airlineStr} ${fbBadge} &middot; ${durStr}</div>
  `;

  return card;
}

// ── Boot ───────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
