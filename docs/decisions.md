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

### 008: Keep WhoScored's full match-centre JSON as the raw record
**Date:** 2026-10-19
soccerdata's default WhoScored output is a trimmed events table. The page actually holds much more (lineups, positions, formation changes by minute, referee, venue), and we'll need those for minutes played and positional filters. We store the whole match-centre object, so nothing has to be re-scraped later.

### 009: Raw files are gzip-compressed and written atomically
**Date:** 2026-10-19
A WhoScored match is ~1.2 MB of JSON and ~96 KB gzipped (about 12×), so a full season is ~35 MB rather than ~450 MB. Each file is written to a `.tmp` file and then renamed, so a crash or Ctrl+C never leaves a half-written file that looks valid.

### 010: One idempotent ingest command
**Date:** 2026-10-19
`python -m pipeline.ingest` fetches every finished match we don't already have, from every source. Running it twice does nothing the second time (idempotent). A failure on one match is logged and the rest carry on, and the exit code is non-zero so a scheduler can tell something failed.

### 011: Heatmaps use counted zones, not smoothed density, for single matches
**Date:** 2026-10-19
One player in one match has roughly 50–120 touches. A smoothed (KDE) heatmap with that few points shows confident-looking blobs that are mostly noise. A 6×5 grid with the count printed in each zone shows exactly what happened. Smoothed heatmaps can come back for season-level views, where there are thousands of touches.

### 012: Fix — WhoScored backfill was 10× slower than it needed to be
**Date:** 2026-10-19
The first full backfill ran at ~107 s per match (~2 hours for the season). Reading soccerdata's source showed that `read_events()` re-downloads the 10-page fixture list on every call unless `force_cache=True`. Our run already fetches a fresh fixture list once at the start, so passing `force_cache=True` is safe, and it brought each match down to ~10 s. **Lesson:** time each step and read the library's code before blaming the website.

### 013: Our own event key, because WhoScored's event `id` isn't unique
**Date:** 2026-10-19
Validation found two different events sharing one `id` in a match (an `OffsideGiven` reusing the id of a real pass or tackle). Joining on that id would quietly pair the wrong events. Each event is now keyed by `(match_id, event_index)`, its position in the match's event list, and the provider id is kept as `source_event_id` for reference only.

### 014: Unknown heights/ages are stored as missing, not 0
**Date:** 2026-10-19
WhoScored reports 0 cm for players with no recorded height. pandera's range check caught it on the first run. We convert 0 to null in bronze, so averages ("average height of a back four") aren't dragged towards zero.

### 015: dbt for the silver/gold layers, with silver materialised as tables
**Date:** 2026-10-19
Stat definitions are SQL in dbt models, version-controlled and tested on every build (`docs/metrics.md` documents each one). Silver started as views but views re-read Parquet through relative paths and re-parse the qualifier JSON on every query, so silver is now materialised as tables (still only a few MB).
**Data tests** run with every build: goals reconcile with final scores; team minutes add up to 11 × match length after red cards; key uniqueness and value ranges.

### 016: One `pipeline.run` command for the whole refresh
**Date:** 2026-10-19
`python -m pipeline.run` = ingest → bronze → `dbt build`. It stops at the first failing step. dbt's output paths are set through environment variables here, because the `dbt_project.yml` settings are deprecated.

### 017: Train xG on StatsBomb open data, and follow its licence
**Date:** 2026-10-21
StatsBomb's free data has full-season shot data with clear terms. The licence (StatsBomb Public Data User Agreement) allows research use but forbids redistribution and **any commercial use of the data or analysis derived from it**, and it requires the StatsBomb logo on anything published from it. So: the data stays in git-ignored `data/`; premistats stays free with no ads or sponsorship while it uses this model; every xG chart and write-up credits StatsBomb.
**Training set:** complete competitions only: the 2015/16 Premier League, La Liga, Serie A and Ligue 1, World Cups 2018/2022 and Euros 2020/2024 (1,747 matches, 43,717 shots). One-club samples (Barcelona-only La Liga seasons, and a 34-match "Bundesliga 2015/16" that is one club's season) are excluded so the model doesn't learn one team's habits.

### 018: One shared shot vocabulary for both providers
**Date:** 2026-10-21
The model trains on StatsBomb shots and scores WhoScored shots, so both are mapped onto the same features (`xg/features.py`, `dbt/models/silver/stg_shots.sql`), and only features both providers record are used: location, body part, situation, first-time, one-on-one, volley, and assist type. StatsBomb's freeze frames (defender positions) and WhoScored's "big chance" flag exist on one side only, so the base model can't use them.

### 019: Gradient boosting chosen over logistic regression; penalties outside the model
**Date:** 2026-10-21
On held-out matches (split by match to stop leakage): baseline log loss 0.2727 / AUC 0.739; logistic 0.2561 / 0.787; gradient boosting 0.2543 / 0.789; StatsBomb's own xG 0.2445 / 0.808 (it can see defender positions). Boosting wins narrowly and stays well calibrated. Penalties get a fixed xG equal to their conversion rate in training (0.73), because a model can't learn anything useful about them from location.

### 020: xG is scored inside dbt (Python model)
**Date:** 2026-10-21
`dbt/models/silver/shot_xg.py` is a dbt Python model, so xG sits in the same lineage and tests as every SQL stat (every shot gets exactly one xG, between 0 and 1). The trained model file comes from `python -m xg.train` and lives in `data/models/` (git-ignored, since it's derived from StatsBomb data).

### 021: Finding: the base model under-rates big chances, so add a calibration stage
**Date:** 2026-10-21
Against Understat on 2026/27, our xG agrees per team per match (r = 0.89) but totals 18% lower (189 vs 232; actual goals 195). Splitting by WhoScored's big-chance flag shows why: big chances convert at 31.6% but we average 24.6%, while other shots convert at 5.1% against our 6.2%. Without defender positions, the model can't tell a tap-in from a crowded shot taken from the same spot.
**Plan:** keep the StatsBomb model and add a small calibration stage (logistic regression on the base model's logit + the big-chance flag), **trained on the 2025/26 PL season and tested on 2026/27**, so the test season is never used for fitting.

### 022: Stage 2 calibration results, and what they say about Understat
**Date:** 2026-10-21
Fitted on all 380 matches of 2025/26 and tested on 2026/27 (never used for fitting), non-penalty shots: log loss 0.2954 → **0.2736**, ROC AUC 0.721 → **0.759**, sum of xG 181.4 → **185.6** against 187 goals. Agreement with Understat per team-match rose from r = 0.89 to **r = 0.96**.
Our totals now track actual goals (2025/26: 995 xG vs 1,005 goals; 2026/27: 194 vs 195). **Understat's xG totals ran ~18% above actual goals in both seasons** (2025/26: 1,184 vs 1,004), far beyond what luck explains over 380 matches. We report this as an observed difference, not as Understat being "wrong": their model and shot definitions may differ from ours.
**Also:** the minutes test now allows 0. Leny Yoro came on in the 100th, final minute of Man Utd v Liverpool (2025/26): a real appearance with no time on the clock.
**Caveat (worth knowing for interviews):** the fitted slope on the base model's logit is only 0.31, while the big-chance coefficient is 1.99. Once the model knows whether a shot was a big chance, location adds less than you'd expect, so stage 2 leans heavily on WhoScored's (human-judged) big-chance tag. If WhoScored changed how it tags big chances, the calibration would need refitting.
