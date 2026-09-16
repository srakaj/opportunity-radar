const state = { items: [] };

const els = {
  results: document.querySelector('#results'),
  stats: document.querySelector('#stats'),
  search: document.querySelector('#search'),
  minScore: document.querySelector('#minScore'),
  newOnly: document.querySelector('#newOnly'),
  template: document.querySelector('#cardTemplate'),
};

function daysSince(iso) {
  if (!iso) return Infinity;
  const then = new Date(iso).getTime();
  return (Date.now() - then) / 86400000;
}

function formatSignal(signal) {
  return signal.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function render() {
  const needle = els.search.value.trim().toLowerCase();
  const minScore = Number(els.minScore.value);

  const filtered = state.items.filter(item => {
    const haystack = `${item.title || ''} ${item.description || ''} ${item.query || ''}`.toLowerCase();
    if (needle && !haystack.includes(needle)) return false;
    if ((item.score || 0) < minScore) return false;
    if (els.newOnly.checked && daysSince(item.first_seen) > 7) return false;
    return true;
  });

  els.stats.innerHTML = `
    <div><strong>${filtered.length}</strong><span>shown</span></div>
    <div><strong>${state.items.length}</strong><span>stored</span></div>
    <div><strong>${state.items.filter(x => daysSince(x.first_seen) <= 7).length}</strong><span>new this week</span></div>
  `;

  els.results.innerHTML = '';
  if (!filtered.length) {
    els.results.innerHTML = '<p class="empty">No opportunities match these filters yet.</p>';
    return;
  }

  for (const item of filtered) {
    const node = els.template.content.cloneNode(true);
    node.querySelector('.score').textContent = item.score ?? 0;
    const link = node.querySelector('.title');
    link.textContent = item.title || 'Untitled opportunity';
    link.href = item.url;
    node.querySelector('.description').textContent = item.description || '';
    node.querySelector('.meta').textContent = `First seen ${new Date(item.first_seen).toLocaleDateString()} · ${item.source || 'source'}`;

    const positive = (item.reasons || []).filter(r => r.points > 0).slice(0, 6);
    node.querySelector('.signals').innerHTML = positive.map(r => `<span>${formatSignal(r.signal)}</span>`).join('');
    node.querySelector('.reasons').innerHTML = (item.reasons || [])
      .map(r => `<div><span>${formatSignal(r.signal)}</span><strong>${r.points > 0 ? '+' : ''}${r.points}</strong></div>`)
      .join('');
    els.results.appendChild(node);
  }
}

async function init() {
  try {
    const response = await fetch('opportunities.json', { cache: 'no-store' });
    state.items = response.ok ? await response.json() : [];
  } catch {
    state.items = [];
  }
  render();
}

for (const el of [els.search, els.minScore, els.newOnly]) {
  el.addEventListener('input', render);
  el.addEventListener('change', render);
}

init();
