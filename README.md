# Opportunity Radar

A personal opportunity-discovery and ranking pipeline for niche legal, policy, governance, privacy, compliance, legal-tech, human-rights and research roles.

The project is designed to solve a specific retrieval problem: conventional job-search engines are good at popular job titles, but poor at discovering fragmented opportunities such as fellowships, traineeships, pro-bono research roles, working groups, NGO projects and international remote internships.

## What v0.2 does

- polls structured public sources directly instead of relying only on search engines
- supports public Greenhouse and Lever career boards
- searches ReliefWeb's humanitarian jobs API
- searches GitHub Issues for unusual open-source and civic-tech contribution opportunities
- retains broad web discovery for fellowships, NGO calls and other fragmented sources
- normalises all sources into one opportunity schema
- removes duplicates across sources and previous runs
- applies transparent, rule-based relevance scoring
- re-scores history so improved rules automatically remove old false positives
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
Explainable relevance score
      ↓
Deduplication + history
      ↓
JSON data + static dashboard
```

The key design decision is to treat search engines as a **discovery layer**, not as the database. Wherever a structured public source exists, Opportunity Radar queries it directly.

## Repository structure

```text
config/
  preferences.yaml       scoring weights and exclusions
  queries.yaml           broad web-search vocabulary
  sources.yaml           structured source configuration
radar/
  adapters.py            Greenhouse, Lever, ReliefWeb and GitHub adapters
  search.py              general web discovery
  score.py               explainable rule-based ranking
scripts/
  run_radar.py           pipeline entry point
tests/                    regression tests
data/                     machine-readable opportunity history
docs/                     static GitHub Pages dashboard
.github/workflows/        scheduled daily run
```

## Direct sources

### Greenhouse

Add a public board token to `config/sources.yaml`:

```yaml
greenhouse:
  boards:
    - token: wikimedia
      name: Wikimedia Foundation
```

The adapter retrieves all currently published jobs from the board's public Job Board API and scores them locally.

### Lever

```yaml
lever:
  sites:
    - site: atlassian
      name: Atlassian
      instance: global
```

Both global and EU Lever instances are supported.

### ReliefWeb

ReliefWeb is searched directly for legal, policy, governance, human-rights and protection roles. Results are deduplicated before entering the scoring pipeline.

### GitHub Issues

GitHub's Issues Search API is used to surface opportunities that conventional job boards rarely contain, for example open-source legal-tech, privacy, governance, documentation, civic-tech and open-data contributions. The daily GitHub Actions token is used for authenticated public search.

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

Edit `config/preferences.yaml` to change scoring weights and exclusions.

Edit `config/queries.yaml` to change broad search vocabulary. The query builder deliberately searches naming variants rather than relying on one literal job title.

Edit `config/sources.yaml` to add or remove structured ATS boards and API searches.

## Dashboard

The static dashboard lives in `docs/` and is published through GitHub Pages from the `main` branch's `/docs` directory.

## Daily automation

`.github/workflows/daily-radar.yml` runs every morning, executes regression tests, searches all configured sources, and commits changed opportunity data back to the repository. It can also be started manually from the Actions tab.

## Design principles

1. **Structured sources first.** Prefer the actual public ATS/API over search-engine snippets whenever possible.
2. **Explainable ranking.** Every score can be traced to explicit positive and negative signals.
3. **High recall, then filtering.** Search broadly, but keep the final dataset selective.
4. **No query leakage.** Search terms themselves never count as evidence that a result is relevant.
5. **History is re-evaluated.** Improving the algorithm also cleans previously stored results.
6. **No paid dependency.** The pipeline can run entirely on GitHub Actions and public endpoints.
7. **Extensible adapters.** New ATS platforms and direct NGO/think-tank monitors can be added without rewriting the pipeline.

## Roadmap

- v0.3: direct Ashby and Workable adapters
- v0.4: fetch detail pages and extract deadline, compensation and eligibility
- v0.5: NGO / think-tank / fellowship source monitors
- v0.6: optional LLM classification for ambiguous eligibility and role type
- v0.7: email digest, closing-soon alerts and application tracking

## Licence

MIT
