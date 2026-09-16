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

function formatDate(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('de-DE');
}

function formatSource(source = '') {
  if (source.startsWith('greenhouse:')) {
    return `Greenhouse · ${source.split(':')[1]}`;
  }
  if (source.startsWith('lever:')) {
    return `Lever · ${source.split(':')[1]}`;
  }
  if (source.startsWith('reliefweb')) return 'ReliefWeb';
  if (source.startsWith('github')) return 'GitHub Issues';
  return source || 'Source';
}

function parseStructuredDescription(description = '') {
  const fields = {};
  let body = description.trim();

  const definitions = [
    ['organisation', 'Organisation'],
    ['location', 'Location'],
    ['department', 'Department'],
    ['office', 'Office'],
    ['commitment', 'Commitment'],
    ['team', 'Team'],
    ['categories', 'Career categories'],
    ['deadline', 'Application deadline'],
  ];

  // Adapters prepend structured metadata before the free-form advert body.
  // Peel off only those leading fields so matching words inside the advert are untouched.
  let matched = true;
  while (matched && body) {
    matched = false;
    for (const [key, label] of definitions) {
      const pattern = new RegExp(`^${label}:\\s*([^.]*)\\.\\s*`, 'i');
      const result = body.match(pattern);
      if (result) {
        fields[key] = result[1].trim();
        body = body.slice(result[0].length).trim();
        matched = true;
        break;
      }
    }
  }

  return { fields, body };
}

function addMetaItem(container, label, value) {
  if (!value) return;
  const item = document.createElement('div');
  item.className = 'meta-item';

  const strong = document.createElement('strong');
  strong.textContent = `${label}: `;
  item.appendChild(strong);
  item.appendChild(document.createTextNode(value));
  container.appendChild(item);
}

function render() {
  const needle = els.search.value.trim().toLowerCase();
  const minScore = Number(els.minScore.value);

  const filtered = state.items.filter(item => {
    const reasonText = (item.reasons || []).map(r => r.signal || '').join(' ');
    const haystack = [
      item.title,
      item.organization,
      item.location,
      item.description,
      item.source,
      reasonText,
    ].filter(Boolean).join(' ').toLowerCase();

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
    const parsed = parseStructuredDescription(item.description || '');

    node.querySelector('.score').textContent = item.score ?? 0;

    const titleLink = node.querySelector('.title');
    titleLink.textContent = item.title || 'Untitled opportunity';
    titleLink.href = item.url || '#';

    const openRole = node.querySelector('.open-role');
    openRole.href = item.url || '#';

    node.querySelector('.topline').textContent =
      `First seen ${formatDate(item.first_seen)} · ${formatSource(item.source)}`;

    const meta = node.querySelector('.meta-grid');
    addMetaItem(meta, 'Organisation', parsed.fields.organisation || item.organization);
    addMetaItem(meta, 'Location', parsed.fields.location || item.location);
    addMetaItem(meta, 'Department', parsed.fields.department);
    addMetaItem(meta, 'Team', parsed.fields.team);
    addMetaItem(meta, 'Office', parsed.fields.office);
    addMetaItem(meta, 'Commitment', parsed.fields.commitment);
    addMetaItem(meta, 'Categories', parsed.fields.categories);
    addMetaItem(meta, 'Deadline', parsed.fields.deadline || item.deadline);
    if (!meta.children.length) meta.hidden = true;

    const description = node.querySelector('.description');
    const body = parsed.body || item.description || '';
    description.textContent = body;

    const toggle = node.querySelector('.toggle-description');
    if (body.length > 420) {
      description.classList.add('clamped');
      toggle.hidden = false;
      toggle.addEventListener('click', () => {
        const isClamped = description.classList.toggle('clamped');
        toggle.textContent = isClamped ? 'Show more' : 'Show less';
      });
    }

    const positive = (item.reasons || []).filter(r => r.points > 0).slice(0, 8);
    const signals = node.querySelector('.signals');
    for (const reason of positive) {
      const chip = document.createElement('span');
      chip.textContent = formatSignal(reason.signal);
      signals.appendChild(chip);
    }

    const reasons = node.querySelector('.reasons');
    for (const reason of item.reasons || []) {
      const row = document.createElement('div');
      const label = document.createElement('span');
      const points = document.createElement('strong');
      label.textContent = formatSignal(reason.signal);
      points.textContent = `${reason.points > 0 ? '+' : ''}${reason.points}`;
      row.append(label, points);
      reasons.appendChild(row);
    }

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
