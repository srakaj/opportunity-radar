# Opportunity Radar

A personal opportunity-discovery and ranking pipeline for niche legal, policy, governance, privacy, compliance, legal-tech, human-rights and research roles.

The project is designed to solve a specific retrieval problem: conventional job-search engines are good at popular job titles, but poor at discovering fragmented opportunities such as fellowships, traineeships, pro-bono research roles, working groups, NGO projects and international remote internships.

## What v0.1 does

- expands a compact preference profile into many search queries
- normalises discovered results into a common opportunity schema
- removes duplicates across searches and previous runs
- applies transparent, rule-based relevance scoring
- preserves previously discovered opportunities
- publishes a static browser dashboard
- can run automatically every day with GitHub Actions

## Architecture

```text
Search sources
    ↓
Normalise results
    ↓
Rule-based classification
    ↓
Eligibility / exclusion checks
    ↓
Explainable relevance score
    ↓
Deduplication + history
    ↓
JSON data + static dashboard
```

## Repository structure

```text
config/                 search vocabulary and personal ranking preferences
radar/                  Python package
scripts/                command-line entry points
data/                   machine-readable opportunity history
docs/                   static dashboard for GitHub Pages
.github/workflows/       scheduled daily run
```

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python scripts/run_radar.py
```

The resulting dataset is written to `data/opportunities.json` and copied to `docs/opportunities.json` for the dashboard.

## Configure it

Edit `config/preferences.yaml` to change scoring weights, preferred topics and exclusions.

Edit `config/queries.yaml` to change role families, topics, locations and source-specific searches. The query builder deliberately searches synonyms rather than relying on one literal job title.

## Dashboard

The static dashboard lives in `docs/`. To publish it with GitHub Pages, use **Settings → Pages → Deploy from a branch → `main` → `/docs`**.

## Daily automation

`.github/workflows/daily-radar.yml` runs every morning and commits newly discovered opportunities back to the repository. It can also be started manually from the Actions tab.

## Design principles

1. **Explainable ranking.** Every score can be traced to explicit positive and negative signals.
2. **High recall first.** Search broadly, then discard irrelevant results.
3. **No fake precision.** v0.1 does not pretend to infer facts that are not visible in a source.
4. **No paid dependency.** The initial pipeline can run entirely on GitHub Actions.
5. **Extensible sources.** Dedicated Greenhouse, Lever, NGO, GitHub and direct-site adapters can be added later.

## Roadmap

- v0.2: fetch source pages and extract deadlines, compensation and eligibility
- v0.3: Greenhouse and Lever adapters
- v0.4: direct NGO / think-tank monitors and GitHub issue discovery
- v0.5: optional LLM classification layer
- v0.6: email digest and closing-soon alerts

## Licence

MIT
