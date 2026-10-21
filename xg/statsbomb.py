"""Download StatsBomb open data and keep only what the xG model needs: shots.

Each match's full event file (~3 MB) is fetched, its shots are extracted
(~1% of the file), and the rest is thrown away, so ~6.5 GB of downloads
become a few MB on disk. Per-match results are saved as they finish, which
makes the download safe to stop and re-run.

StatsBomb's licence: research use, no redistribution, no commercial use, and
credit the StatsBomb logo on anything published from it (decision 017).

Usage:
    python -m xg.statsbomb
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from pipeline.config import DATA_DIR

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
OUT_DIR = DATA_DIR / "external" / "statsbomb"
SHOTS_DIR = OUT_DIR / "shots"

# Only complete competitions: one-club samples (e.g. Barcelona-only La Liga
# seasons) would teach the model how one team's chances behave. Bundesliga
# 2015/16 looks complete in the competition list but holds only 34 matches
# (one club's season), so it is left out too.
COMPETITIONS = {
    (2, 27): "Premier League 2015/16",
    (11, 27): "La Liga 2015/16",
    (12, 27): "Serie A 2015/16",
    (7, 27): "Ligue 1 2015/16",
    (43, 3): "World Cup 2018",
    (43, 106): "World Cup 2022",
    (55, 43): "Euro 2020",
    (55, 282): "Euro 2024",
}


def fetch_json(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def _name(d: dict | None, key: str):
    return (d or {}).get(key, {}).get("name")


def extract_shots(events: list[dict], match: dict, competition: str) -> list[dict]:
    by_id = {e["id"]: e for e in events}
    shots = []
    for e in events:
        if e["type"]["name"] != "Shot":
            continue
        s = e["shot"]
        key_pass = by_id.get(s.get("key_pass_id"), {}).get("pass", {})
        shots.append({
            "match_id": match["match_id"],
            "competition": competition,
            "shot_id": e["id"],
            "period": e["period"],
            "minute": e["minute"],
            # StatsBomb pitch is 120 x 80 with the shooter attacking towards x = 120.
            "x": e["location"][0],
            "y": e["location"][1],
            "body_part": _name(s, "body_part"),
            "shot_type": _name(s, "type"),
            "technique": _name(s, "technique"),
            "play_pattern": e["play_pattern"]["name"],
            "first_time": bool(s.get("first_time", False)),
            "one_on_one": bool(s.get("one_on_one", False)),
            "under_pressure": bool(e.get("under_pressure", False)),
            "assisted": bool(key_pass),
            "assist_cross": bool(key_pass.get("cross", False)),
            "assist_through_ball": bool(key_pass.get("through_ball", False))
                or _name(key_pass, "technique") == "Through Ball",
            "assist_height": _name(key_pass, "height"),
            "statsbomb_xg": s.get("statsbomb_xg"),
            "outcome": _name(s, "outcome"),
            "is_goal": _name(s, "outcome") == "Goal",
        })
    return shots


def download_match(match: dict, competition: str) -> int:
    out = SHOTS_DIR / f"{match['match_id']}.json"
    if out.exists():
        return -1
    events = fetch_json(f"{BASE}/events/{match['match_id']}.json")
    shots = extract_shots(events, match, competition)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(shots), encoding="utf-8")
    tmp.replace(out)
    return len(shots)


def main() -> None:
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for (comp_id, season_id), name in COMPETITIONS.items():
        matches = fetch_json(f"{BASE}/matches/{comp_id}/{season_id}.json")
        jobs += [(m, name) for m in matches]
        print(f"{name}: {len(matches)} matches")

    done = sum((SHOTS_DIR / f"{m['match_id']}.json").exists() for m, _ in jobs)
    print(f"{len(jobs)} matches in total, {done} already downloaded")

    start, finished, failed = time.monotonic(), 0, []
    # A few parallel downloads: polite to GitHub, but ~6x faster than one at a time.
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(download_match, m, name): m["match_id"] for m, name in jobs}
        for f in as_completed(futures):
            try:
                if f.result() >= 0:
                    finished += 1
                    if finished % 100 == 0:
                        rate = finished / (time.monotonic() - start)
                        print(f"  {finished} downloaded ({rate:.1f}/s)", flush=True)
            except Exception as e:
                failed.append(futures[f])
                print(f"  FAILED {futures[f]}: {e}", flush=True)

    # Build the table from this run's competitions only (older downloads may hold others).
    files = [SHOTS_DIR / f"{m['match_id']}.json" for m, _ in jobs]
    files = [f for f in files if f.exists()]
    df = pd.DataFrame([s for f in files for s in json.loads(f.read_text(encoding="utf-8"))])
    df.to_parquet(OUT_DIR / "shots.parquet", index=False)
    print(f"Saved {len(df):,} shots from {len(files)} matches to {(OUT_DIR / 'shots.parquet').name}")
    if failed:
        sys.exit(f"{len(failed)} matches failed; re-run to retry them")


if __name__ == "__main__":
    main()
