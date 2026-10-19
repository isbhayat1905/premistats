# premistats

Free, advanced Premier League stats and visualisations: shot maps, heatmaps, xG, pass networks and a build-your-own chart tool. Focused on the 2026/27 season.

> 🚧 Early development. Currently: the ingestion pipeline and prototype charts.

![Shot map: Nottingham Forest 0–1 Arsenal](docs/img/shot_map_31248.png)

## How it works

```
scrapers (soccerdata) → data/raw (immutable JSON per match)
   → bronze Parquet (schema checks) → dbt models (silver → gold)
   → exported aggregates → static website (Next.js + DuckDB-WASM)
```

Design choices and trade-offs are logged in [docs/decisions.md](docs/decisions.md).

## Running it locally

Requires Python 3.12.

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m pipeline.ingest_match                       # save the latest finished match
python -m analysis.shot_map data/raw/understat/2627/<match_id>.json
```

## Data & attribution

Data is collected from public match centres (currently Understat). Raw scraped data is never republished. The site shows only derived statistics, our own model outputs and charts. If you're a rights holder with concerns, please open an issue.
