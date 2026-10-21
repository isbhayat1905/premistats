# premistats roadmap

**Started:** Mon 19 Oct 2026
**Website MVP (public beta):** Mon 14 Dec 2026
**Full release (v1.0):** Sun 31 Jan 2027

Estimates assume roughly **10–15 hours a week**. Each phase includes a few days' slack, because scraped sources can break without warning (decision 003).

---

## Timeline

| Phase | Dates | Goal | Status |
|---|---|---|---|
| 1. Foundations & pipeline | 19 Oct | Data in, cleaned, tested | ✅ Done |
| 2. xG model | 20 Oct – 1 Nov | Our own xG, trained and evaluated | ⏳ In progress (v1 done 21 Oct) |
| 3. Match & team analytics | 2 Nov – 15 Nov | Match pages' data, team style, export layer | |
| 4. Website MVP | 16 Nov – 13 Dec | Live site with the core visuals | |
| 🚀 **Public beta** | **14 Dec** | Shareable before the busy Christmas fixtures | |
| 5. Advanced metrics | 15 Dec – 10 Jan | xT, radars, comparisons | |
| 6. Past season + polish | 11 Jan – 31 Jan | 2025/26 archive, write-ups, performance | |
| 🏁 **Full release v1.0** | **31 Jan** | Complete, documented, on your CV | |

---

## Phase 1: Foundations & pipeline ✅ (19 Oct 2026)

- [x] Project plan agreed: free site, PL 2026/27, £0 hosting
- [x] Tools installed: Python 3.12, Node 24, Git, Chrome, VS Code Python extension
- [x] Git repo with your name on the commits (7 commits on day one)
- [x] Found that 2025/26 has finished and switched the target to **2026/27** (2025/26 becomes the first archive season)
- [x] Source adapter pattern: swappable plug-ins for Understat (shots/xG) and WhoScored (full event data)
- [x] Raw layer: one compressed, never-overwritten file per match (1.2 MB → 96 KB)
- [x] `pipeline.ingest`: fetches only new matches and carries on past failures
- [x] Fixed a 10× slowdown in the WhoScored fetch (107 s → 10 s per match)
- [x] Backfilled all 69 played matches from both sources: 105,906 events, 1,904 shots, 0 failures
- [x] Bronze layer: 4 Parquet tables with pandera validation (caught 0 cm heights and duplicate event IDs)
- [x] dbt silver/gold models: minutes (with stoppage time and red cards), 28 stats + per 90
- [x] 21 automated data tests, including "goals reconcile with final scores"
- [x] `pipeline.run`: the whole refresh in one command
- [x] Prototype charts: shot map, touch map + zone heatmap, X/Y scatter
- [x] Docs: README, 16 entries in `decisions.md`, `metrics.md`, this roadmap

## Phase 2: xG model (20 Oct – 1 Nov)

- [x] Download StatsBomb open data: 1,747 matches, 43,717 shots (licence rules: decision 017)
- [x] Feature engineering with one shared vocabulary for both providers (decision 018)
- [x] Train baseline, logistic regression and gradient boosting (boosting chosen)
- [x] Evaluate: log loss, Brier, ROC AUC, calibration plot, feature importance → `docs/xg_model.md`
- [x] Apply to WhoScored shots inside dbt (Python model `shot_xg`) + 3 new tests
- [x] Compare against Understat: r = 0.89 per team-match, but 18% lower → big chances under-rated (decision 021)
- [ ] Backfill 2025/26 (brought forward from Phase 6) and train the big-chance calibration stage on it
- [ ] Re-validate calibrated xG on 2026/27
- [x] Add xG / npxG / xA / goals − xG / npxG per shot to `player_season_stats`
- [ ] Link players across WhoScored and Understat (names differ, e.g. accents)
- [ ] ✍️ **You write:** "Building an xG model from scratch" (write-up #1)

## Phase 3: Match & team analytics (2 Nov – 15 Nov)

- [ ] `match_stats` and `team_match_stats` gold tables
- [ ] xG timeline ("xG race") data per match
- [ ] Pass networks: average positions + pass counts between players
- [ ] Team style: PPDA (pressing), field tilt, defensive line height
- [ ] Season-level smoothed heatmaps (enough touches for density to be meaningful)
- [ ] Export layer: gold tables → small Parquet/JSON files for the website
- [ ] Weekly scheduled refresh with Windows Task Scheduler
- [ ] Data-freshness and test-results summary (for a "data quality" page)
- [ ] Spot-check 5 players' goals, shots and minutes against the official PL site

## Phase 4: Website MVP (16 Nov – 13 Dec)

- [ ] Accounts: GitHub (push the repo) and Vercel
- [ ] Next.js + TypeScript + Tailwind project in `web/`, deployed to `premistats.vercel.app`
- [ ] Shared chart style (colour palette, light/dark mode) matching the prototypes
- [ ] Player pages: season stats, per 90, shot map, touch map/heatmap
- [ ] Team pages: results, team style metrics, top players
- [ ] Match pages: score, xG race, shot map, pass networks
- [ ] **X/Y chart builder**: any two stats, minutes/position/team filters, highlighted players
- [ ] DuckDB-WASM so the chart builder queries data in the browser (no server)
- [ ] PNG export with premistats watermark; shareable links that keep chart settings
- [ ] Mobile layout, fast loading (Lighthouse ≥ 85), Open Graph preview images
- [ ] About page: data sources, attribution, metric definitions, AI-assisted build statement
- [ ] Privacy-friendly analytics (Vercel Analytics)

## 🚀 Public beta (Mon 14 Dec)

- [ ] Post on r/FantasyPL and football-analytics X/Bluesky with a watermarked chart
- [ ] Start a weekly "chart of the matchweek" post
- [ ] Collect feedback (simple form or GitHub issues)

## Phase 5: Advanced metrics (15 Dec – 10 Jan)

- [ ] Expected threat (xT) model and per-player xT from passes
- [ ] Progressive carries (inferred from the gaps between events)
- [ ] Percentile ranks by position; radar / pizza charts
- [ ] Player comparison page (two or three players side by side)
- [ ] ✍️ **You write:** analysis piece #2 (e.g. "Who is underrated by xT?")

## Phase 6: Past season + polish (11 Jan – 31 Jan)

- [ ] Backfill 2025/26 (all 380 matches) and add a season switcher on the site
- [ ] GitHub Actions CI: lint, dbt tests on sample data, site build; badges in the README
- [ ] Performance and accessibility pass; fix beta feedback
- [ ] README as a case study: architecture diagram, lineage, lessons learned
- [ ] ✍️ **You write:** write-up #3 + a LinkedIn post announcing v1.0
- [ ] Add the live URL and GitHub link to your CV

## 🏁 Full release v1.0 (Sun 31 Jan 2027)

---

### Later (after v1.0)
- Custom domain (premistats.com / .co.uk, about £10 a year)
- Other leagues (the pipeline is already per-league)
- Mobile app
- Possession value model (VAEP) using the event data
