# Opportunity Radar

A personal opportunity-discovery, enrichment and fit-ranking pipeline for niche legal, policy, governance, privacy, compliance, legal-tech, AI-governance, human-rights and research roles.

The project is designed to solve a specific retrieval problem: conventional job-search engines are good at popular job titles, but poor at discovering fragmented opportunities such as fellowships, traineeships, legal working-student roles, research calls, NGO projects and unusual open-source contributions.

## What v0.4 does

- polls structured public sources directly instead of relying only on search engines
- supports public Greenhouse and Lever career boards
- searches ReliefWeb and GitHub Issues for unusual opportunities
- retains broad web discovery for fellowships, NGO calls and fragmented sources
- normalises all sources into one opportunity schema
- extracts structured opportunity metadata such as type, work model, compensation, duration, deadlines, start dates, languages, eligibility and work-authorisation wording
- removes duplicates across sources and previous runs
- applies transparent, rule-based **relevance scoring**
- separately applies a transparent **personal-fit assessment**
- labels opportunities `Strong fit`, `Stretch` or `Probably skip`
- explains positive fit signals, gaps and hard blockers
- re-evaluates stored history whenever extraction or ranking rules improve
- publishes a static browser dashboard
- runs automatically every day with GitHub Actions
- runs regression tests before each scheduled search

## Architecture

```text
Greenhouse ─┐
Lever ──────┤
ReliefWeb ──┤
GitHub ─────┤
Web search ─┘
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
Deduplication + history
      ↓
JSON data + static dashboard
```

The key design decision is to keep **retrieval relevance** and **candidate fit** separate. A role can be highly relevant to the target domains while still being a poor current fit because of seniority, qualification, language or work-authorisation requirements.

## Repository structure

```text
config/
  preferences.yaml       relevance-scoring weights and exclusions
  profile.yaml           public-safe professional fit signals
  queries.yaml           broad web-search vocabulary
  sources.yaml           structured source configuration
radar/
  adapters.py            Greenhouse, Lever, ReliefWeb and GitHub adapters
  enrich.py              structured opportunity metadata extraction
  enrichment_score.py    reconciliation between enrichment and relevance score
  fit.py                 explainable personal-fit assessment
  search.py              general web discovery
  score.py               explainable rule-based relevance ranking
scripts/
  run_radar.py           pipeline entry point
tests/                    regression tests
data/                     machine-readable opportunity history
docs/                     static GitHub Pages dashboard
.github/workflows/        scheduled daily run
```

## Personal fit layer

`config/profile.yaml` intentionally contains only abstract professional signals because this repository is public. It does not store a CV, employer history or sensitive personal information.

The fit engine considers signals such as:

- current career stage
- student / qualification status
- known languages
- preferred opportunity types
- Berlin / Germany / Europe / remote compatibility
- target legal and policy domains
- professional experience overlap
- explicit eligibility wording
- required qualifications
- work-authorisation restrictions
- seniority and expired deadlines

Each stored opportunity receives:

```text
fit_score
fit_label
fit_reasons
fit_gaps
fit_blockers
```

The dashboard surfaces these independently from the ordinary relevance score.

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

The resulting dataset is written to `data/opportunities.json` and copied to `docs/opportunities.json` for the dashboard.

## Configure it

Edit `config/preferences.yaml` to change relevance-scoring weights and exclusions.

Edit `config/profile.yaml` to change personal-fit assumptions.

Edit `config/queries.yaml` to change broad search vocabulary.

Edit `config/sources.yaml` to add or remove structured ATS boards and API searches.

## Dashboard

The static dashboard lives in `docs/` and is published through GitHub Pages from the `main` branch's `/docs` directory. It supports search, fit-level filtering, relevance-score filtering, new-opportunity filtering, structured metadata and separate explanations for personal fit and thematic relevance.

## Daily automation

`.github/workflows/daily-radar.yml` runs every morning, executes regression tests, searches all configured sources, enriches and ranks the results, and commits changed opportunity data back to the repository.

## Design principles

1. **Structured sources first.** Prefer the actual public ATS/API over search-engine snippets whenever possible.
2. **Relevance is not fit.** Thematic relevance and candidate suitability are calculated separately.
3. **Explainable ranking.** Scores and fit labels are traceable to explicit signals.
4. **High recall, then filtering.** Search broadly, but keep the final dataset selective.
5. **No query leakage.** Search terms themselves never count as evidence that a result is relevant.
6. **History is re-evaluated.** Improving the algorithm also cleans previously stored results.
7. **Public-safe configuration.** Personal fit uses abstract professional signals rather than a detailed private profile.
8. **No paid dependency.** The pipeline can run entirely on GitHub Actions and public endpoints.

## Roadmap

- v0.5: richer direct NGO / think-tank / fellowship source monitors and additional ATS adapters
- v0.6: optional semantic classification for ambiguous requirements and eligibility
- v0.7: closing-soon alerts and digest delivery
- v0.8: application tracking (`Saved`, `Applying`, `Applied`, `Interview`, `Offer`, `Rejected`)

## Licence

MIT
