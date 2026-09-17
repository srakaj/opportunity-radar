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
      for (const key of [...url.searchParams.keys()]) {
        const lower = key.toLowerCase();
        if (lower.startsWith('utm_') || ['source', 'src', 'ref', 'referrer', 'gh_src', 'lever-source'].includes(lower)) {
          url.searchParams.delete(key);
        }
      }
      const pathname = url.pathname === '/' ? '/' : url.pathname.replace(/\/$/, '');
      url.pathname = pathname;
      return url.href.replace(/\?$/, '').replace(/#$/, '');
    } catch {
      return String(value).split('#', 1)[0].replace(/\/$/, '');
    }
  }

  function formatBerlin(iso) {
    if (!iso) return '';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    const parts = Object.fromEntries(
      BERLIN_FORMATTER.formatToParts(date)
        .filter(part => part.type !== 'literal')
        .map(part => [part.type, part.value])
    );
    return `${parts.day}.${parts.month}.${parts.year} ${parts.hour}:${parts.minute}`;
  }

  function slug(value = '') {
    return String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }

  function findMeta(meta, labelText) {
    return [...meta.querySelectorAll('.meta-item')].find(node => {
      const strong = node.querySelector('strong');
      return strong && strong.textContent.trim().toLowerCase().startsWith(labelText.toLowerCase());
    });
  }

  function createMeta(meta, labelText) {
    let row = findMeta(meta, labelText);
    if (!row) {
      row = document.createElement('div');
      row.className = 'meta-item';
      meta.appendChild(row);
    }
    row.replaceChildren();
    const label = document.createElement('strong');
    label.textContent = `${labelText}: `;
    row.appendChild(label);
    return row;
  }

  function enhanceCard(card, item) {
    const meta = card.querySelector('.meta-grid');
    if (!meta || !item) return;
    meta.hidden = false;

    if (item.source_quality) {
      const row = createMeta(meta, 'Source quality');
      row.className = `meta-item source-quality-meta source-quality-${slug(item.source_quality)}`;
      const value = document.createElement('span');
      value.className = 'source-quality-value';
      value.textContent = item.source_quality;
      row.appendChild(value);

      const duplicates = Number(item.duplicate_count || 0);
      if (duplicates > 0) {
        const note = document.createElement('small');
        note.className = 'source-duplicate-note';
        note.textContent = `· ${duplicates} duplicate${duplicates === 1 ? '' : 's'} merged`;
        row.appendChild(note);
      }
      row.title = item.source_quality_label || '';
    }

    const checked = formatBerlin(item.last_checked || item.last_seen);
    if (checked) {
      const row = createMeta(meta, 'Last checked');
      const value = document.createElement('span');
      value.className = 'source-last-seen-value';
      value.textContent = checked;
      row.appendChild(value);
      row.title = 'Last time this opportunity was confirmed by a discovery source.';
    }
  }

  function renderHealth(health) {
    const stats = document.querySelector('#stats');
    if (!stats || !health || !health.summary) return;

    document.querySelector('.source-health-shell')?.remove();
    const shell = document.createElement('section');
    shell.className = 'source-health-shell';
    shell.setAttribute('aria-label', 'Source health');

    const details = document.createElement('details');
    const summary = document.createElement('summary');
    const main = document.createElement('span');
    main.className = 'source-health-summary-main';

    const totals = health.summary;
    const dot = document.createElement('span');
    dot.className = 'source-health-dot';
    if (Number(totals.error || 0) > 0) dot.classList.add('error');
    else if (Number(totals.degraded || 0) > 0) dot.classList.add('degraded');

    const strong = document.createElement('strong');
    strong.textContent = `Sources ${totals.healthy || 0}/${totals.total || 0} healthy`;
    main.append(dot, strong);

    if (Number(totals.degraded || 0) > 0 || Number(totals.error || 0) > 0) {
      const issues = document.createElement('span');
      issues.className = 'source-health-muted';
      const parts = [];
      if (totals.degraded) parts.push(`${totals.degraded} degraded`);
      if (totals.error) parts.push(`${totals.error} error${totals.error === 1 ? '' : 's'}`);
      issues.textContent = `· ${parts.join(' · ')}`;
      main.appendChild(issues);
    }

    const generated = document.createElement('span');
    generated.className = 'source-health-generated';
    const generatedLabel = formatBerlin(health.generated_at);
    generated.textContent = generatedLabel ? `Last run ${generatedLabel}` : 'Awaiting first V0.6 run';

    summary.append(main, generated);
    details.appendChild(summary);

    const grid = document.createElement('div');
    grid.className = 'source-health-grid';
    for (const source of health.sources || []) {
      const item = document.createElement('div');
      item.className = `source-health-item source-health-status-${source.status || 'unknown'}`;

      const name = document.createElement('strong');
      name.textContent = source.label || source.id || 'Source';

      const info = document.createElement('span');
      const statusLabel = source.status === 'healthy'
        ? 'healthy'
        : source.status === 'degraded'
          ? 'degraded'
          : source.status === 'error'
            ? 'error'
            : 'unknown';
      info.textContent = `${source.kind || 'Source'} · ${statusLabel} · ${Number(source.rows || 0)} rows`;
      if (source.error) item.title = source.error;
      item.append(name, info);
      grid.appendChild(item);
    }

    if ((health.sources || []).length) details.appendChild(grid);
    shell.appendChild(details);
    stats.insertAdjacentElement('afterend', shell);
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
    const [itemsResult, healthResult] = await Promise.allSettled([
      fetch('opportunities.json', { cache: 'no-store' }).then(response => response.ok ? response.json() : []),
      fetch('source-health.json', { cache: 'no-store' }).then(response => response.ok ? response.json() : null),
    ]);

    const items = itemsResult.status === 'fulfilled' && Array.isArray(itemsResult.value)
      ? itemsResult.value
      : [];
    const health = healthResult.status === 'fulfilled' ? healthResult.value : null;
    if (health) renderHealth(health);

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
