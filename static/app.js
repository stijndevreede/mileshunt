// MilesHunt — Frontend logic

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let groups = [];
let activeGroups = new Set();

// ── Init ───────────────────────────────────────────────────

async function init() {
  // Set default date to tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  $('#date').value = tomorrow.toISOString().split('T')[0];

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
  $('#xp-ref-toggle').addEventListener('click', () => {
    const panel = $('#xp-ref');
    panel.hidden = !panel.hidden;
  });
}

function renderGroupChips() {
  const container = $('#group-chips');
  container.innerHTML = '';

  for (const g of groups) {
    const chip = document.createElement('button');
    chip.className = 'chip' + (g.default_on ? ' active' : '');
    chip.textContent = g.label;
    chip.title = g.description;
    chip.dataset.id = g.id;

    if (g.default_on) activeGroups.add(g.id);

    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
      if (activeGroups.has(g.id)) {
        activeGroups.delete(g.id);
      } else {
        activeGroups.add(g.id);
      }
    });

    container.appendChild(chip);
  }
}

// ── Hunt ───────────────────────────────────────────────────

async function runHunt() {
  const origin = $('#origin').value.trim().toUpperCase() || 'AMS';
  const date = $('#date').value;
  const cabin = $('#cabin').value;

  if (!date) {
    showStatus('Please select a date.', false);
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
    const resp = await fetch('/api/hunt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin,
        date,
        cabin,
        groups: [...activeGroups],
      }),
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
  $('#stat-multi').textContent = deals.filter(d => d.segments >= 3).length;
  $('#stat-excellent').textContent = deals.filter(d => d.rating === 'EXCELLENT').length;

  // Cards
  deals.forEach((deal, i) => {
    container.appendChild(createCard(deal, i + 1));
  });
}

function createCard(deal, rank) {
  const card = document.createElement('div');
  const ratingClass = deal.rating.toLowerCase();
  card.className = `card card-border-${ratingClass}`;

  const airlineStr = deal.airline_names.join(', ');
  const fbBadge = deal.all_fb
    ? '<span class="fb-badge fb-yes">All FB</span>'
    : '<span class="fb-badge fb-no">Mixed</span>';

  let breakdownHTML = '';
  if (deal.xp_breakdown) {
    breakdownHTML = deal.xp_breakdown.map(seg => {
      const fbNote = seg.earns_fb ? '' : '<span class="seg-no-fb">no FB</span>';
      return `<div class="seg">
        <span class="seg-route">${seg.from} &gt; ${seg.to}</span>
        <span class="seg-airline">${seg.airline}</span>
        <span class="seg-xp">${seg.xp} XP</span>
        <span class="seg-band">${seg.band}</span>
        ${fbNote}
      </div>`;
    }).join('');
  }

  card.innerHTML = `
    <div class="card-top">
      <span class="card-rank">#${rank}</span>
      <span class="card-rating rating-${ratingClass}">${deal.rating}</span>
    </div>
    <div class="card-route">${deal.route}</div>
    <div class="card-metrics">
      <div class="metric">
        <div class="metric-value price">$${Math.round(deal.price).toLocaleString()}</div>
        <div class="metric-label">Price</div>
      </div>
      <div class="metric">
        <div class="metric-value xp">${deal.xp}</div>
        <div class="metric-label">XP (one-way)</div>
      </div>
      <div class="metric">
        <div class="metric-value xp">${deal.xp_rt}</div>
        <div class="metric-label">XP (RT est.)</div>
      </div>
      <div class="metric">
        <div class="metric-value per-xp">$${deal.per_xp}</div>
        <div class="metric-label">$/XP</div>
      </div>
    </div>
    <div class="card-breakdown">${breakdownHTML}</div>
    <div class="card-airlines">${airlineStr} ${fbBadge} &middot; ${deal.segments} seg &middot; ${Math.floor(deal.duration / 60)}h${deal.duration % 60}m</div>
  `;

  return card;
}

// ── Boot ───────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
