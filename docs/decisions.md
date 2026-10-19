# Decisions log

One entry per meaningful choice: what we picked, why, and what we didn't pick.
Newest at the bottom.

---

### 001: Target season is 2026/27 (2025/26 becomes the first archive season)
**Date:** 2026-10-19
The project began as "this season = 2025/26", but that season is complete (380/380 matches). The season in progress is 2026/27 (69 matches played at the time of writing). We build for 2026/27 and backfill 2025/26 as the first past season, which also tests that the pipeline really is per-season.

### 002: Use the soccerdata library for scraping
**Date:** 2026-10-19
One Python library wraps Understat, WhoScored, FBref and Sofascore with on-disk caching and polite request handling. Writing our own scrapers would take weeks and add nothing to the analysis.
**Rejected:** hand-written requests/BeautifulSoup scrapers; paid APIs (budget is £0).

### 003: Source adapter pattern
**Date:** 2026-10-19
Every source implements one interface (`pipeline/sources/base.py`). Downstream code never imports a source directly. Scraped sources can block us or change their format without warning, and this way swapping a source touches one file.

### 004: Raw data is immutable, one JSON file per match, and never committed or republished
**Date:** 2026-10-19
`data/raw/<source>/<season>/<match_id>.json` is written once, along with when it was fetched. Every later layer can be rebuilt from it, so a bug in cleaning code never forces a re-scrape. The `data/` folder is git-ignored: the public site shows only derived aggregates, model outputs and charts, never the scraped raw data.

### 005: Shots from Understat first; full event data (WhoScored) second
**Date:** 2026-10-19
Understat works over plain HTTP. WhoScored needs a real Chrome browser to get past bot protection. Shots + xG let us prove the pipeline end to end on day one, and event data (touches, passes) is layered on afterwards.

### 006: Pitch coordinates are normalised to the Opta 0–100 convention
**Date:** 2026-10-19
Understat uses 0–1 and WhoScored uses 0–100 (Opta). We convert everything to 0–100 with the team in possession attacking towards x = 100, so every chart and model uses one coordinate system.

### 007: Chart colours come from a validated, colour-blind-safe palette
**Date:** 2026-10-19
Home = blue `#2a78d6`, away = orange `#eb6834` (categorical slots 1–2). Goal vs no goal uses filled vs hollow markers as well as colour, so the chart still reads for colour-blind viewers and in greyscale.
