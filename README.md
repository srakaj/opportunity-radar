# Opportunity Radar

A personal opportunity-discovery, enrichment, fit-ranking and application-tracking pipeline for niche legal, policy, governance, privacy, compliance, legal-tech, AI-governance, human-rights and research roles.

The project is designed to solve a specific retrieval problem: conventional job-search engines are good at popular job titles, but poor at discovering fragmented opportunities such as fellowships, traineeships, legal working-student roles, research calls, NGO projects and unusual open-source contributions.

## What v0.6 does

- polls structured public sources directly instead of relying only on search engines
- supports public Greenhouse, Lever and Ashby career boards
- searches ReliefWeb and GitHub Issues for unusual opportunities
- monitors a curated watchlist of legal-tech, privacy, digital-rights and AI-governance organisations on their official domains
- retains broad web discovery for fellowships, NGO calls and fragmented sources
- assigns source provenance and quality (`Official ATS`, `Official site`, `Curated board`, `Open source`, `Web discovery`)
- prefers direct official sources when the same role is discovered more than once
- deduplicates equivalent roles across ATS feeds, official websites and search discovery
- writes a source-health report on every run and exposes it in the dashboard
- records when each opportunity was last confirmed by a discovery source
- normalises all sources into one opportunity schema
- extracts structured opportunity metadata such as type, work model, compensation, duration, deadlines, start dates, languages, eligibility and work-authorisation wording
- applies transparent rule-based **relevance scoring**
- separately applies a transparent **personal-fit assessment**
- labels opportunities `Strong fit`, `Stretch` or `Probably skip`
- explains positive fit signals, gaps and hard blockers
- adds a private browser-side **application workspace**
- tracks `Saved`, `Interested`, `Applying`, `Applied`, `Interview`, `Offer`, `Rejected` and `Archived` stages
- stores personal application deadlines and notes locally in the browser
- keeps tracked opportunities visible even after they disappear from the current discovery feed
- supports workspace JSON export/import for backup and browser migration
- publishes a static browser dashboard
- runs automatically every day with GitHub Actions
- runs regression tests before each scheduled search

## Architecture

```text
Greenhouse ─────┐
Lever ──────────┤
Ashby ──────────┤
ReliefWeb ──────┤
GitHub ─────────┤
Official-site ──┤  curated organisation watchlist
Web search ─────┘
       ↓
Source provenance + quality
       ↓
Normalise to common schema
       ↓
Opportunity / seniority checks
       ↓
Metadata enrichment
       ↓
Explainable relevance score
       ↓
Personal fit assessment
       ↓
Strong fit / Stretch / Probably skip
       ↓
Cross-source deduplication + history
       ↓
JSON data + source-health report + static dashboard
       ↓
Private browser application workspace
```

The key design decision is to keep **retrieval relevance**, **candidate fit**, **source confidence**, and **application state** separate. A role can be highly relevant but a poor current fit; a tracked application can also remain useful after the source advert disappears.

## Repository structure

```text
config/
  preferences.yaml       relevance-scoring weights and exclusions
  profile.yaml           public-safe professional fit signals
  queries.yaml           broad web-search vocabulary
  sources.yaml           direct ATS sources + organisation watchlist
radar/
  adapters.py            Greenhouse, Lever, ReliefWeb and GitHub adapters
  source_expansion.py    Ashby, watchlist, source quality and cross-source dedupe
  enrich.py              structured opportunity metadata extraction
  enrichment_score.py    reconciliation between enrichment and relevance score
  fit.py                 explainable personal-fit assessment
  search.py              general web discovery
  score.py               explainable rule-based relevance ranking
scripts/
  run_radar.py           pipeline entry point
tests/                    regression tests
data/                     machine-readable opportunity history
docs/                     static GitHub Pages dashboard + browser workspace
.github/workflows/        scheduled daily run
```

## Source intelligence

V0.6 distinguishes where a result came from rather than treating all URLs equally.

Source priority is currently:

```text
Official ATS        100
Official site        90
Curated board        75
Open source          65
Web discovery        40
```

When two records represent the same role, the higher-quality source becomes canonical. Missing metadata can still be retained from the lower-priority record, and the dashboard can show that duplicates were merged.

Each opportunity can receive:

```text
source_quality
source_priority
source_quality_label
alternate_sources
duplicate_count
last_checked
```

The daily run also writes `docs/source-health.json`. The dashboard shows how many configured sources were healthy, degraded or in error, along with row counts and the last run time.

## Organisation watchlist

`config/sources.yaml` contains a curated watchlist for organisations worth checking even when no supported public ATS endpoint is known. Each watch is constrained to the organisation's official domain and is treated as higher-confidence than generic web discovery.

Example:

```yaml
watchlist:
  enabled: true
  organizations:
    - name: BRYTER
      domain: bryter.com
    - name: noyb
      domain: noyb.eu
```

The current watchlist covers legal-tech companies plus privacy, digital-rights and AI-governance organisations. It can be expanded without changing code.

## Personal fit layer

`config/profile.yaml` intentionally contains only abstract professional signals because this repository is public. It does not store a CV, employer history or sensitive personal information.

The fit engine considers signals such as career stage, qualification status, languages, preferred opportunity types, geography, target domains, professional experience overlap, explicit eligibility wording, work-authorisation restrictions and seniority.

Each stored opportunity receives:

```text
fit_score
fit_label
fit_reasons
fit_gaps
fit_blockers
```

The dashboard surfaces these independently from the ordinary relevance score.

## Application workspace

The application workspace is intentionally **not committed to the public repository**. Statuses, notes and personal deadlines are stored in browser `localStorage` under a versioned key.

Supported stages:

```text
Untracked
Saved
Interested
Applying
Applied
Interview
Offer
Rejected
Archived
```

Each tracked opportunity can also store a personal application deadline and free-text notes. The dashboard can filter by application stage and sort by personal deadline, personal fit, recency or relevance.

When a tracked opportunity disappears from the daily discovery feed, the workspace preserves a compact local snapshot so the application record remains visible. It is marked as no longer present in the current feed so the user can verify whether the original role has closed.

Because browser storage is device/browser-local, the workspace supports JSON **Export** and **Import**. Exported files can be used as backups or moved to another browser. No application notes are uploaded by the normal radar pipeline.

## Direct sources

### Greenhouse

Add a public board token to `config/sources.yaml`:

```yaml
greenhouse:
  boards:
    - token: wikimedia
      name: Wikimedia Foundation
```

### Lever

```yaml
lever:
  sites:
    - site: example
      name: Example Company
      instance: global
```

Both global and EU Lever instances are supported.

### Ashby

```yaml
ashby:
  boards:
    - board: harvey
      name: Harvey
```

V0.6 currently watches Harvey, Legora and Robin AI through their public Ashby job boards.

### ReliefWeb

ReliefWeb is queried directly for legal, policy, governance, human-rights and protection roles.

### GitHub Issues

GitHub Issues Search surfaces opportunities that conventional job boards rarely contain, including open-source legal-tech, privacy, governance, documentation and research contributions.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/run_radar.py
```

The resulting dataset is written to `data/opportunities.json` and copied to `docs/opportunities.json` for the dashboard. Source diagnostics are written to `docs/source-health.json`.

## Configure it

Edit `config/preferences.yaml` to change relevance-scoring weights and exclusions.

Edit `config/profile.yaml` to change personal-fit assumptions.

Edit `config/queries.yaml` to change broad search vocabulary.

Edit `config/sources.yaml` to add or remove structured ATS boards, API searches and watched organisations.

## Dashboard

The static dashboard lives in `docs/` and is published through GitHub Pages from the `main` branch's `/docs` directory. It supports search, fit-level filtering, relevance-score filtering, application-stage filtering, personal-deadline sorting, new-opportunity filtering, structured metadata, source provenance, source-health diagnostics, personal-fit explanations and private application tracking.

## Daily automation

`.github/workflows/daily-radar.yml` runs every morning, executes regression tests, searches all configured sources, enriches and ranks the results, writes source-health diagnostics, and commits changed opportunity data back to the repository. Browser application state is not touched by this workflow.

## Design principles

1. **Structured sources first.** Prefer the actual public ATS/API over search-engine snippets whenever possible.
2. **Official beats discovered.** If the same role appears in multiple places, preserve the best original source.
3. **Relevance is not fit.** Thematic relevance and candidate suitability are calculated separately.
4. **Application state is private.** Tracking notes and personal deadlines stay browser-local unless explicitly exported by the user.
5. **Explainable ranking.** Scores and fit labels are traceable to explicit signals.
6. **Source health is observable.** A broken feed should be visible instead of silently reducing coverage.
7. **High recall, then filtering.** Search broadly, but keep the final dataset selective.
8. **No query leakage.** Search terms themselves never count as evidence that a result is relevant.
9. **History is re-evaluated.** Improving the algorithm also cleans previously stored discovery results.
10. **Tracked applications survive source removal.** Closing an advert does not erase the user's application record.
11. **Public-safe configuration.** Personal fit uses abstract professional signals rather than a detailed private profile.
12. **No paid dependency.** The pipeline can run entirely on GitHub Actions and public endpoints.

## Roadmap

- v0.7: closing-soon alerts and high-signal daily digest delivery
- v0.8: per-opportunity application brief / application-preparation assistant
- v0.9: outcome analytics and optional private cross-device workspace sync

## Licence

MIT
