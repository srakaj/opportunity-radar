const WORKSPACE_KEY = 'opportunity-radar-workspace-v1';
const WORKSPACE_VERSION = 1;
const WORKSPACE_STAGES = [
  'Untracked',
  'Saved',
  'Interested',
  'Applying',
  'Applied',
  'Interview',
  'Offer',
  'Rejected',
  'Archived',
];
const PIPELINE_STAGES = ['Saved', 'Interested', 'Applying', 'Applied', 'Interview', 'Offer'];

const state = {
  items: [],
  workspace: {},
  storageAvailable: true,
};

const els = {
  results: document.querySelector('#results'),
  stats: document.querySelector('#stats'),
  search: document.querySelector('#search'),
  fitFilter: document.querySelector('#fitFilter'),
  minScore: document.querySelector('#minScore'),
  newOnly: document.querySelector('#newOnly'),
  stageFilter: document.querySelector('#stageFilter'),
  sortOrder: document.querySelector('#sortOrder'),
  pipelineStats: document.querySelector('#pipelineStats'),
  exportWorkspace: document.querySelector('#exportWorkspace'),
  importWorkspace: document.querySelector('#importWorkspace'),
  importWorkspaceFile: document.querySelector('#importWorkspaceFile'),
  workspaceStorageNote: document.querySelector('#workspaceStorageNote'),
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
  if (source.startsWith('greenhouse:')) return `Greenhouse · ${source.split(':')[1]}`;
  if (source.startsWith('lever:')) return `Lever · ${source.split(':')[1]}`;
  if (source.startsWith('reliefweb')) return 'ReliefWeb';
  if (source.startsWith('github')) return 'GitHub Issues';
  if (source === 'workspace') return 'Application workspace';
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

function stageClass(stage = '') {
  return `stage-${stage.toLowerCase().replace(/[^a-z]+/g, '-')}`;
}

function canonicalOpportunityKey(item) {
  const rawUrl = String(item?.url || '').split('#', 1)[0].replace(/\/+$/, '');
  if (rawUrl) return rawUrl;
  return `${item?.organization || ''}::${item?.title || ''}`.trim().toLowerCase();
}

function workspaceSnapshot(item) {
  return {
    title: item.title || '',
    url: item.url || '',
    organization: item.organization || '',
    location: item.location || '',
    opportunity_type: item.opportunity_type || '',
    work_model: item.work_model || '',
    fit_label: item.fit_label || '',
    fit_score: item.fit_score ?? null,
    score: item.score ?? null,
    first_seen: item.first_seen || '',
  };
}

function emptyWorkspaceEntry() {
  return {
    status: 'Untracked',
    deadline: '',
    notes: '',
    updatedAt: '',
    snapshot: null,
  };
}

function getWorkspaceEntry(item) {
  const key = canonicalOpportunityKey(item);
  return { ...emptyWorkspaceEntry(), ...(state.workspace[key] || {}) };
}

function loadWorkspace() {
  try {
    const raw = localStorage.getItem(WORKSPACE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    state.storageAvailable = false;
    return {};
  }
}

function persistWorkspace() {
  try {
    localStorage.setItem(WORKSPACE_KEY, JSON.stringify(state.workspace));
    state.storageAvailable = true;
    return true;
  } catch {
    state.storageAvailable = false;
    return false;
  }
}

function updateWorkspace(item, patch) {
  const key = canonicalOpportunityKey(item);
  const current = getWorkspaceEntry(item);
  const next = {
    ...current,
    ...patch,
    status: WORKSPACE_STAGES.includes(patch.status || current.status)
      ? (patch.status || current.status)
      : 'Untracked',
    snapshot: current.snapshot || workspaceSnapshot(item),
    updatedAt: new Date().toISOString(),
  };

  const meaningful = next.status !== 'Untracked' || next.deadline || String(next.notes || '').trim();
  if (meaningful) state.workspace[key] = next;
  else delete state.workspace[key];
  persistWorkspace();
}

function clearWorkspace(item) {
  delete state.workspace[canonicalOpportunityKey(item)];
  persistWorkspace();
}

function trackedWorkspaceItems() {
  const currentKeys = new Set(state.items.map(canonicalOpportunityKey));
  const extras = [];

  for (const [key, entry] of Object.entries(state.workspace)) {
    if (!entry || entry.status === 'Untracked' || currentKeys.has(key) || !entry.snapshot) continue;
    const snapshot = entry.snapshot;
    extras.push({
      ...snapshot,
      source: 'workspace',
      workspace_only: true,
      description: 'This opportunity is no longer in the current discovery feed. It is kept here because you are tracking it. Open the original role and verify whether it is still available.',
      reasons: [],
      fit_reasons: [],
      fit_gaps: ['No longer in the current discovery feed; verify that the opportunity is still open.'],
      fit_blockers: [],
    });
  }
  return extras;
}

function allDisplayItems() {
  return [...state.items, ...trackedWorkspaceItems()];
}

function personalDeadlineMeta(value) {
  if (!value) return { label: '', className: '' };
  const target = new Date(`${value}T12:00:00`);
  if (Number.isNaN(target.getTime())) return { label: value, className: '' };

  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const days = Math.round((target.getTime() - today.getTime()) / 86400000);
  const dateLabel = target.toLocaleDateString('de-DE');

  if (days < 0) return { label: `${dateLabel} · overdue by ${Math.abs(days)}d`, className: 'deadline-overdue' };
  if (days === 0) return { label: `${dateLabel} · due today`, className: 'deadline-today' };
  if (days <= 7) return { label: `${dateLabel} · due in ${days}d`, className: 'deadline-soon' };
  return { label: dateLabel, className: '' };
}

function compareForSort(a, b, sortOrder) {
  if (sortOrder === 'deadline') {
    const aValue = getWorkspaceEntry(a).deadline || '9999-12-31';
    const bValue = getWorkspaceEntry(b).deadline || '9999-12-31';
    if (aValue !== bValue) return aValue.localeCompare(bValue);
  }
  if (sortOrder === 'newest') {
    return String(b.first_seen || '').localeCompare(String(a.first_seen || ''));
  }
  if (sortOrder === 'relevance') {
    return (Number(b.score) || 0) - (Number(a.score) || 0);
  }

  const fitDiff = (Number(b.fit_score) || 0) - (Number(a.fit_score) || 0);
  if (fitDiff) return fitDiff;
  return (Number(b.score) || 0) - (Number(a.score) || 0);
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

function renderPipelineStats(items) {
  const counts = Object.fromEntries(WORKSPACE_STAGES.map(stage => [stage, 0]));
  for (const item of items) counts[getWorkspaceEntry(item).status] += 1;

  const tracked = items.filter(item => getWorkspaceEntry(item).status !== 'Untracked').length;
  els.pipelineStats.replaceChildren();

  const trackedButton = document.createElement('button');
  trackedButton.type = 'button';
  trackedButton.dataset.stage = 'tracked';
  trackedButton.innerHTML = `<strong>${tracked}</strong><span>Tracked</span>`;
  els.pipelineStats.appendChild(trackedButton);

  for (const stage of PIPELINE_STAGES) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.stage = stage;
    button.innerHTML = `<strong>${counts[stage]}</strong><span>${stage}</span>`;
    els.pipelineStats.appendChild(button);
  }

  for (const button of els.pipelineStats.querySelectorAll('button')) {
    const stage = button.dataset.stage;
    if (els.stageFilter.value === stage) button.classList.add('active');
    button.addEventListener('click', () => {
      els.stageFilter.value = stage;
      render();
    });
  }
}

function renderWorkspaceControls(node, item) {
  const workspace = getWorkspaceEntry(item);
  const panel = node.querySelector('.workspace-panel');
  const summary = node.querySelector('.workspace-stage-summary');
  const badge = node.querySelector('.workspace-stage-badge');
  const saveButton = node.querySelector('.save-opportunity');
  const statusSelect = node.querySelector('.workspace-status');
  const deadlineInput = node.querySelector('.workspace-deadline');
  const deadlineState = node.querySelector('.workspace-deadline-state');
  const notes = node.querySelector('.workspace-notes');
  const updated = node.querySelector('.workspace-updated');
  const clearButton = node.querySelector('.clear-workspace');

  summary.textContent = workspace.status;
  summary.classList.add(stageClass(workspace.status));

  if (workspace.status !== 'Untracked') {
    badge.hidden = false;
    badge.textContent = workspace.status;
    badge.classList.add(stageClass(workspace.status));
    saveButton.textContent = workspace.status === 'Saved' ? 'Saved ✓' : 'Tracking ✓';
    saveButton.classList.add('is-saved');
  }

  for (const stage of WORKSPACE_STAGES) {
    const option = document.createElement('option');
    option.value = stage;
    option.textContent = stage;
    statusSelect.appendChild(option);
  }
  statusSelect.value = workspace.status;
  deadlineInput.value = workspace.deadline || '';
  notes.value = workspace.notes || '';

  const deadlineMeta = personalDeadlineMeta(workspace.deadline);
  deadlineState.textContent = deadlineMeta.label;
  if (deadlineMeta.className) deadlineState.classList.add(deadlineMeta.className);

  if (workspace.updatedAt) updated.textContent = `Last updated ${formatDate(workspace.updatedAt)}`;
  else updated.textContent = 'Not tracked yet';

  saveButton.addEventListener('click', () => {
    const current = getWorkspaceEntry(item);
    if (current.status === 'Untracked') {
      updateWorkspace(item, { status: 'Saved' });
      render();
    } else {
      panel.open = true;
    }
  });

  statusSelect.addEventListener('change', () => {
    updateWorkspace(item, { status: statusSelect.value });
    render();
  });

  deadlineInput.addEventListener('change', () => {
    updateWorkspace(item, { deadline: deadlineInput.value });
    render();
  });

  notes.addEventListener('input', () => {
    updateWorkspace(item, { notes: notes.value });
    updated.textContent = 'Saved in this browser just now';
  });

  clearButton.addEventListener('click', () => {
    const ok = window.confirm('Clear status, personal deadline and notes for this opportunity?');
    if (!ok) return;
    clearWorkspace(item);
    render();
  });
}

function render() {
  const displayItems = allDisplayItems();
  const needle = els.search.value.trim().toLowerCase();
  const minScore = Number(els.minScore.value);
  const fitFilter = els.fitFilter.value;
  const stageFilter = els.stageFilter.value;

  renderPipelineStats(displayItems);

  const filtered = displayItems.filter(item => {
    const workspace = getWorkspaceEntry(item);
    const reasonText = (item.reasons || []).map(r => r.signal || '').join(' ');
    const fitText = [
      item.fit_label,
      ...(item.fit_reasons || []),
      ...(item.fit_gaps || []),
      ...(item.fit_blockers || []),
    ].join(' ');
    const workspaceText = [workspace.status, workspace.deadline, workspace.notes].join(' ');
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
      workspaceText,
    ].filter(Boolean).join(' ').toLowerCase();

    if (needle && !haystack.includes(needle)) return false;
    if ((item.score || 0) < minScore) return false;
    if (fitFilter !== 'all' && item.fit_label !== fitFilter) return false;
    if (stageFilter === 'tracked' && workspace.status === 'Untracked') return false;
    if (!['all', 'tracked'].includes(stageFilter) && workspace.status !== stageFilter) return false;
    if (els.newOnly.checked && daysSince(item.first_seen) > 7) return false;
    return true;
  }).sort((a, b) => compareForSort(a, b, els.sortOrder.value));

  const trackedCount = displayItems.filter(item => getWorkspaceEntry(item).status !== 'Untracked').length;
  els.stats.innerHTML = `
    <div><strong>${filtered.length}</strong><span>shown</span></div>
    <div><strong>${state.items.length}</strong><span>current feed</span></div>
    <div><strong>${state.items.filter(x => x.fit_label === 'Strong fit').length}</strong><span>strong fits</span></div>
    <div><strong>${trackedCount}</strong><span>tracked</span></div>
  `;

  if (!state.storageAvailable) {
    els.workspaceStorageNote.textContent = 'Browser storage is unavailable. Workspace edits will not survive a reload.';
    els.workspaceStorageNote.classList.add('storage-warning');
  } else {
    els.workspaceStorageNote.textContent = 'Statuses, deadlines and notes stay in this browser. Export a backup if you want to move them elsewhere.';
    els.workspaceStorageNote.classList.remove('storage-warning');
  }

  els.results.innerHTML = '';
  if (!filtered.length) {
    els.results.innerHTML = '<p class="empty">No opportunities match these filters yet.</p>';
    return;
  }

  for (const item of filtered) {
    const node = els.template.content.cloneNode(true);
    const parsed = parseStructuredDescription(item.description || '');

    const card = node.querySelector('.card');
    if (item.workspace_only) card.classList.add('workspace-only');

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

    node.querySelector('.topline').textContent = item.workspace_only
      ? 'Tracked workspace record · no longer in current feed'
      : `First seen ${formatDate(item.first_seen)} · ${formatSource(item.source)}`;

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
    const personalDeadline = personalDeadlineMeta(getWorkspaceEntry(item).deadline);
    addMetaItem(meta, 'My deadline', personalDeadline.label);
    if (!meta.children.length) meta.hidden = true;

    renderFitList(
      node.querySelector('.fit-reasons-list'),
      item.fit_reasons,
      item.workspace_only ? 'Fit details unavailable in the saved snapshot.' : 'No strong profile-specific signal extracted yet.'
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

    renderWorkspaceControls(node, item);

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

function exportWorkspace() {
  const payload = {
    format: 'opportunity-radar-workspace',
    version: WORKSPACE_VERSION,
    exportedAt: new Date().toISOString(),
    items: state.workspace,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `opportunity-radar-workspace-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function sanitiseImportedWorkspace(items) {
  if (!items || typeof items !== 'object' || Array.isArray(items)) return {};
  const cleaned = {};
  for (const [key, raw] of Object.entries(items)) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) continue;
    const status = WORKSPACE_STAGES.includes(raw.status) ? raw.status : 'Untracked';
    cleaned[key] = {
      status,
      deadline: typeof raw.deadline === 'string' ? raw.deadline : '',
      notes: typeof raw.notes === 'string' ? raw.notes : '',
      updatedAt: typeof raw.updatedAt === 'string' ? raw.updatedAt : '',
      snapshot: raw.snapshot && typeof raw.snapshot === 'object' ? raw.snapshot : null,
    };
  }
  return cleaned;
}

async function importWorkspaceFile(file) {
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    const imported = sanitiseImportedWorkspace(parsed.items || parsed);
    const count = Object.keys(imported).length;
    if (!count) throw new Error('No workspace records found');
    state.workspace = { ...state.workspace, ...imported };
    persistWorkspace();
    render();
    window.alert(`Imported ${count} workspace record${count === 1 ? '' : 's'}.`);
  } catch (error) {
    window.alert(`Could not import workspace: ${error.message || 'invalid JSON file'}`);
  } finally {
    els.importWorkspaceFile.value = '';
  }
}

async function init() {
  state.workspace = loadWorkspace();
  try {
    const response = await fetch('opportunities.json', { cache: 'no-store' });
    state.items = response.ok ? await response.json() : [];
  } catch {
    state.items = [];
  }
  render();
}

for (const el of [els.search, els.fitFilter, els.minScore, els.newOnly, els.stageFilter, els.sortOrder]) {
  el.addEventListener('input', render);
  el.addEventListener('change', render);
}

els.exportWorkspace.addEventListener('click', exportWorkspace);
els.importWorkspace.addEventListener('click', () => els.importWorkspaceFile.click());
els.importWorkspaceFile.addEventListener('change', () => importWorkspaceFile(els.importWorkspaceFile.files?.[0]));

init();
