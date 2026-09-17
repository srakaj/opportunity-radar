const state = { items: [] };

const els = {
  results: document.querySelector('#results'),
  stats: document.querySelector('#stats'),
  search: document.querySelector('#search'),
  fitFilter: document.querySelector('#fitFilter'),
  minScore: document.querySelector('#minScore'),
  newOnly: document.querySelector('#newOnly'),
  template: document.querySelector('#cardTemplate'),
};

const DESCRIPTION_HEADINGS = [
  ['Summary', ['Summary']],
  ['Description', ['Description']],
  ['About the role', ['About the role', 'About the Role', 'About this role', 'About the job', 'About the Job']],
  ['Responsibilities', ['Responsibilities', 'Your responsibilities', 'Your Responsibilities', 'What you’ll do', "What you'll do", 'What You’ll Do', "What You'll Do", 'What you will do']],
  ['Requirements', ['Requirements', 'What you’ll bring', "What you'll bring", 'What You’ll Bring', "What You'll Bring"]],
  ['Qualifications', ['Qualifications', 'Minimum qualifications', 'Minimum Qualifications', 'Preferred qualifications', 'Preferred Qualifications']],
  ['Who you are', ['Who you are', 'Who You Are']],
  ['What we’re looking for', ['What we’re looking for', "What we're looking for", 'What We’re Looking For', "What We're Looking For"]],
  ['Benefits', ['Benefits', 'What we offer', 'What We Offer', 'Our offer', 'Our Offer']],
  ['How to apply', ['How to apply', 'How to Apply', 'Application process', 'Application Process']],
  ['Deine Aufgaben', ['Deine Aufgaben', 'Ihre Aufgaben', 'Aufgaben', 'Das erwartet dich', 'Das erwartet Sie']],
  ['Dein Profil', ['Dein Profil', 'Ihr Profil', 'Anforderungen', 'Qualifikationen', 'Das bringst du mit', 'Das bringen Sie mit', 'Was du mitbringst']],
  ['Was wir bieten', ['Was wir bieten', 'Wir bieten', 'Unser Angebot']],
  ['Über die Rolle', ['Über die Rolle', 'Über den Job']],
];

const HEADING_LOOKUP = new Map();
for (const [label, variants] of DESCRIPTION_HEADINGS) {
  for (const variant of variants) HEADING_LOOKUP.set(variant, label);
}

const HEADING_PATTERN = [...HEADING_LOOKUP.keys()]
  .sort((a, b) => b.length - a.length)
  .map(value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  .join('|');

const DESCRIPTION_HEADING_RE = new RegExp(`(^|\\s)(${HEADING_PATTERN})\\s*:?(?=\\s|$)`, 'g');

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

function formatCompensation(item) {
  const detail = item.compensation || '';
  switch (item.compensation_status) {
    case 'paid': return detail || 'Paid';
    case 'unpaid': return detail || 'Unpaid';
    case 'funding_possible': return detail ? `Funding possible · ${detail}` : 'Funding possible';
    default: return '';
  }
}

function formatDeadline(item, fallback = '') {
  const value = item.deadline || fallback;
  if (!value) return '';
  const suffix = {
    closing_soon: ' · closing soon',
    expired: ' · expired',
    open: '',
    unknown: '',
  }[item.deadline_status] || '';
  return `${value}${suffix}`;
}

function joinValues(value) {
  if (Array.isArray(value)) return value.filter(Boolean).join(' · ');
  return value || '';
}

function fitClass(label = '') {
  if (label === 'Strong fit') return 'strong';
  if (label === 'Stretch') return 'stretch';
  if (label === 'Probably skip') return 'skip';
  return 'unknown';
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

function parseDescriptionSections(text = '') {
  const body = text.replace(/\s+/g, ' ').trim();
  if (!body) return [];

  const matches = [];
  DESCRIPTION_HEADING_RE.lastIndex = 0;
  let match;
  while ((match = DESCRIPTION_HEADING_RE.exec(body)) !== null) {
    const prefixLength = match[1].length;
    const variant = match[2];
    matches.push({
      start: match.index + prefixLength,
      contentStart: DESCRIPTION_HEADING_RE.lastIndex,
      label: HEADING_LOOKUP.get(variant) || variant,
    });
  }

  if (!matches.length) return [{ label: '', text: body }];

  const sections = [];
  const preamble = body.slice(0, matches[0].start).trim();
  if (preamble) sections.push({ label: '', text: preamble });

  for (let i = 0; i < matches.length; i += 1) {
    const current = matches[i];
    const nextStart = matches[i + 1]?.start ?? body.length;
    const sectionText = body.slice(current.contentStart, nextStart).trim();
    if (sectionText) sections.push({ label: current.label, text: sectionText });
  }

  return sections.length ? sections : [{ label: '', text: body }];
}

function renderDescription(container, text) {
  const sections = parseDescriptionSections(text);
  container.replaceChildren();

  for (const section of sections) {
    const sectionEl = document.createElement('section');
    sectionEl.className = 'description-section';

    if (section.label) {
      const heading = document.createElement('h3');
      heading.textContent = `${section.label}:`;
      sectionEl.appendChild(heading);
    }

    const paragraph = document.createElement('p');
    paragraph.textContent = section.text;
    sectionEl.appendChild(paragraph);
    container.appendChild(sectionEl);
  }

  return sections;
}

function addMetaItem(container, label, value, wide = false) {
  if (!value) return;
  const item = document.createElement('div');
  item.className = wide ? 'meta-item meta-item-wide' : 'meta-item';

  const strong = document.createElement('strong');
  strong.textContent = `${label}: `;
  item.appendChild(strong);
  item.appendChild(document.createTextNode(value));
  container.appendChild(item);
}

function renderFitList(container, values, emptyText = '') {
  container.replaceChildren();
  const items = Array.isArray(values) ? values.filter(Boolean) : [];
  if (!items.length && emptyText) {
    const li = document.createElement('li');
    li.className = 'fit-empty';
    li.textContent = emptyText;
    container.appendChild(li);
    return;
  }
  for (const value of items) {
    const li = document.createElement('li');
    li.textContent = value;
    container.appendChild(li);
  }
}

function render() {
  const needle = els.search.value.trim().toLowerCase();
  const minScore = Number(els.minScore.value);
  const fitFilter = els.fitFilter.value;

  const filtered = state.items.filter(item => {
    const reasonText = (item.reasons || []).map(r => r.signal || '').join(' ');
    const fitText = [
      item.fit_label,
      ...(item.fit_reasons || []),
      ...(item.fit_gaps || []),
      ...(item.fit_blockers || []),
    ].join(' ');
    const haystack = [
      item.title,
      item.organization,
      item.location,
      item.description,
      item.source,
      item.opportunity_type,
      item.work_model,
      item.compensation,
      item.compensation_status,
      item.duration,
      item.commitment,
      item.deadline,
      item.start_date,
      joinValues(item.languages),
      joinValues(item.eligibility),
      item.work_authorization,
      reasonText,
      fitText,
    ].filter(Boolean).join(' ').toLowerCase();

    if (needle && !haystack.includes(needle)) return false;
    if ((item.score || 0) < minScore) return false;
    if (fitFilter !== 'all' && item.fit_label !== fitFilter) return false;
    if (els.newOnly.checked && daysSince(item.first_seen) > 7) return false;
    return true;
  });

  els.stats.innerHTML = `
    <div><strong>${filtered.length}</strong><span>shown</span></div>
    <div><strong>${state.items.length}</strong><span>stored</span></div>
    <div><strong>${state.items.filter(x => x.fit_label === 'Strong fit').length}</strong><span>strong fits</span></div>
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

    node.querySelector('.score-value').textContent = item.score ?? 0;

    const fitBadge = node.querySelector('.fit-badge');
    fitBadge.classList.add(`fit-${fitClass(item.fit_label)}`);
    node.querySelector('.fit-label-text').textContent = item.fit_label || 'Fit pending';
    node.querySelector('.fit-score-value').textContent = Number.isFinite(Number(item.fit_score))
      ? `${item.fit_score}/100`
      : '—';

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
    addMetaItem(meta, 'Type', item.opportunity_type);
    addMetaItem(meta, 'Work model', item.work_model === 'Unspecified' ? '' : item.work_model);
    addMetaItem(meta, 'Compensation', formatCompensation(item));
    addMetaItem(meta, 'Duration', item.duration);
    addMetaItem(meta, 'Commitment', item.commitment || parsed.fields.commitment);
    addMetaItem(meta, 'Deadline', formatDeadline(item, parsed.fields.deadline));
    addMetaItem(meta, 'Start', item.start_date);
    addMetaItem(meta, 'Eligibility', joinValues(item.eligibility), true);
    addMetaItem(meta, 'Languages', joinValues(item.languages));
    addMetaItem(meta, 'Department', parsed.fields.department);
    addMetaItem(meta, 'Team', parsed.fields.team);
    addMetaItem(meta, 'Office', parsed.fields.office);
    addMetaItem(meta, 'Categories', parsed.fields.categories);
    addMetaItem(meta, 'Work authorisation', item.work_authorization, true);
    if (!meta.children.length) meta.hidden = true;

    renderFitList(
      node.querySelector('.fit-reasons-list'),
      item.fit_reasons,
      'No strong profile-specific signal extracted yet.'
    );
    renderFitList(
      node.querySelector('.fit-gaps-list'),
      item.fit_gaps,
      'No major gaps detected from the available text.'
    );
    const blockers = item.fit_blockers || [];
    const blockerColumn = node.querySelector('.fit-blockers-column');
    if (blockers.length) {
      blockerColumn.hidden = false;
      renderFitList(node.querySelector('.fit-blockers-list'), blockers);
    }

    const description = node.querySelector('.description');
    const body = parsed.body || item.description || '';
    const sections = renderDescription(description, body);

    const toggle = node.querySelector('.toggle-description');
    if (body.length > 520 || sections.length > 3) {
      description.classList.add('collapsed');
      toggle.hidden = false;
      toggle.addEventListener('click', () => {
        const isCollapsed = description.classList.toggle('collapsed');
        toggle.textContent = isCollapsed ? 'Show more' : 'Show less';
      });
    }

    const positive = (item.reasons || [])
      .filter(r => r.points > 0)
      .filter(r => !(r.signal === 'paid' && item.compensation_status && item.compensation_status !== 'paid'))
      .slice(0, 8);
    const signals = node.querySelector('.signals');
    for (const reason of positive) {
      const chip = document.createElement('span');
      chip.textContent = formatSignal(reason.signal);
      signals.appendChild(chip);
    }

    const reasons = node.querySelector('.reasons');
    for (const reason of item.reasons || []) {
      if (reason.signal === 'paid' && item.compensation_status && item.compensation_status !== 'paid') continue;
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

for (const el of [els.search, els.fitFilter, els.minScore, els.newOnly]) {
  el.addEventListener('input', render);
  el.addEventListener('change', render);
}

init();
