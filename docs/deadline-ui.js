(() => {
  const BERLIN_FORMATTER = new Intl.DateTimeFormat('de-DE', {
    timeZone: 'Europe/Berlin',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

  function canonicalUrl(value = '') {
    try {
      const url = new URL(value, window.location.href);
      url.hash = '';
      return url.href.replace(/\/$/, '');
    } catch {
      return String(value).split('#', 1)[0].replace(/\/$/, '');
    }
  }

  function formatBerlin(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    const parts = Object.fromEntries(
      BERLIN_FORMATTER.formatToParts(date)
        .filter(part => part.type !== 'literal')
        .map(part => [part.type, part.value])
    );
    return `${parts.day}.${parts.month}.${parts.year} ${parts.hour}:${parts.minute}`;
  }

  function confidenceInfo(item) {
    switch (item.deadline_time_confidence) {
      case 'explicit_timezone':
        return {
          className: 'deadline-exact',
          note: '',
          title: `Converted to Europe/Berlin from the timezone stated in the source (${item.deadline_source_timezone || 'explicit timezone'}).`,
        };
      case 'location_inferred':
        return {
          className: 'deadline-inferred',
          note: 'TZ inferred',
          title: `The source gave a time but no timezone. Timezone inferred from the opportunity location as ${item.deadline_source_timezone || 'local time'}, then converted to Europe/Berlin.`,
        };
      case 'date_only':
        return {
          className: 'deadline-assumed',
          note: 'time assumed',
          title: 'The source gave a date but no time. 23:59 Europe/Berlin is used as a fallback assumption.',
        };
      case 'timezone_unknown':
        return {
          className: 'deadline-assumed deadline-tz-unknown',
          note: 'TZ unknown',
          title: 'The source gave a time but its timezone could not be determined reliably. The displayed time is provisionally treated as Europe/Berlin.',
        };
      default:
        return { className: '', note: '', title: '' };
    }
  }

  function findDeadlineMeta(meta) {
    return [...meta.querySelectorAll('.meta-item')].find(node => {
      const strong = node.querySelector('strong');
      return strong && strong.textContent.trim().toLowerCase().startsWith('deadline');
    });
  }

  function getOrCreateDeadlineRow(meta) {
    let row = findDeadlineMeta(meta);
    if (!row) {
      row = document.createElement('div');
      row.className = 'meta-item';
      meta.appendChild(row);
    }
    return row;
  }

  function renderMissingDeadline(row) {
    row.className = 'meta-item deadline-meta deadline-missing';
    row.replaceChildren();

    const label = document.createElement('strong');
    label.textContent = 'Deadline (Berlin): ';
    row.appendChild(label);

    const value = document.createElement('span');
    value.className = 'deadline-value';
    value.textContent = 'Not stated';
    row.appendChild(value);

    row.title = 'No application deadline was stated or could be extracted from the current opportunity data.';
  }

  function enhanceCard(card, item) {
    const signature = item?.deadline_berlin_iso
      ? `${item.deadline_berlin_iso}|${item.deadline_time_confidence}`
      : 'deadline-missing';
    if (card.dataset.deadlineEnhanced === signature) return;

    const meta = card.querySelector('.meta-grid');
    if (!meta) return;
    meta.hidden = false;

    const row = getOrCreateDeadlineRow(meta);

    if (!item?.deadline_berlin_iso) {
      renderMissingDeadline(row);
      card.dataset.deadlineEnhanced = signature;
      return;
    }

    const display = formatBerlin(item.deadline_berlin_iso);
    if (!display) {
      renderMissingDeadline(row);
      card.dataset.deadlineEnhanced = 'deadline-invalid';
      return;
    }

    const info = confidenceInfo(item);
    row.className = `meta-item deadline-meta ${info.className}`.trim();
    row.replaceChildren();

    const label = document.createElement('strong');
    label.textContent = 'Deadline (Berlin): ';
    row.appendChild(label);

    const value = document.createElement('span');
    value.className = 'deadline-value';
    value.textContent = display;
    row.appendChild(value);

    if (info.note) {
      const note = document.createElement('small');
      note.className = 'deadline-note';
      note.textContent = info.note;
      row.appendChild(note);
    }

    const status = item.deadline_status;
    if (status === 'closing_soon' || status === 'expired') {
      const statusEl = document.createElement('small');
      statusEl.className = `deadline-status deadline-status-${status}`;
      statusEl.textContent = status === 'closing_soon' ? 'closing soon' : 'expired';
      row.appendChild(statusEl);
    }

    const original = item.deadline_original ? ` Source: ${item.deadline_original}.` : '';
    row.title = `${info.title}${original}`.trim();
    card.dataset.deadlineEnhanced = signature;
  }

  function enhanceAll(itemsByUrl) {
    document.querySelectorAll('#results .card').forEach(card => {
      const link = card.querySelector('a.title');
      if (!link) return;
      const item = itemsByUrl.get(canonicalUrl(link.href));
      if (item) enhanceCard(card, item);
    });
  }

  async function init() {
    let items = [];
    try {
      const response = await fetch('opportunities.json', { cache: 'no-store' });
      if (response.ok) items = await response.json();
    } catch {
      return;
    }

    const itemsByUrl = new Map(
      items.filter(item => item?.url).map(item => [canonicalUrl(item.url), item])
    );

    const results = document.querySelector('#results');
    if (!results) return;

    let queued = false;
    const schedule = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        enhanceAll(itemsByUrl);
      });
    };

    new MutationObserver(schedule).observe(results, { childList: true, subtree: true });
    schedule();
  }

  init();
})();
