"""Bronze layer: flatten raw match files into typed Parquet tables.

Bronze is a faithful, tabular copy of the raw data: same meaning, same values,
just one row per thing with proper column types. No business logic here; derived
values like minutes played or progressive passes belong in the dbt models.

Every table is rebuilt from data/raw on each run (a full season takes seconds),
then validated with pandera before it's written.

Usage:
    python -m pipeline.bronze
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from pipeline.config import DATA_DIR, RAW_DIR
from pipeline.raw import read_raw
from pipeline.schemas import SCHEMAS

BRONZE_DIR = DATA_DIR / "bronze"


def _display(value):
    """WhoScored wraps enums as {"displayName": ..., "value": ...}; keep the name."""
    return value["displayName"] if isinstance(value, dict) else value


def whoscored_tables(path: Path) -> dict[str, list[dict]]:
    raw = read_raw(path)
    season, match_id, m = raw["season"], raw["match_id"], raw["data"]
    home_goals, away_goals = (int(g) for g in m["ftScore"].split(" : "))

    match = {
        "match_id": match_id,
        "season": season,
        "kickoff_local": m["startTime"],
        "home_team_id": m["home"]["teamId"],
        "home_team": m["home"]["name"],
        "away_team_id": m["away"]["teamId"],
        "away_team": m["away"]["name"],
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_manager": m["home"].get("managerName"),
        "away_manager": m["away"].get("managerName"),
        "venue": m.get("venueName"),
        "attendance": m.get("attendance"),
        "referee": (m.get("referee") or {}).get("name"),
        "max_minute_expanded": m["expandedMaxMinute"],
        "fetched_at": raw["fetched_at"],
    }

    players = []
    for side in ("home", "away"):
        for p in m[side]["players"]:
            players.append({
                "match_id": match_id,
                "team_id": m[side]["teamId"],
                "player_id": p["playerId"],
                "player": p["name"],
                "shirt_no": p.get("shirtNo"),
                "position": p.get("position"),
                "is_starter": bool(p.get("isFirstEleven", False)),
                "subbed_in_minute": p.get("subbedInExpandedMinute"),
                "subbed_out_minute": p.get("subbedOutExpandedMinute"),
                # WhoScored uses 0 for "unknown"; store it as missing so averages aren't dragged down.
                "age": p.get("age") or None,
                "height_cm": p.get("height") or None,
            })

    events = []
    for i, e in enumerate(m["events"]):
        events.append({
            "match_id": match_id,
            # Our own key: position in the match's event stream. WhoScored's `id` is
            # NOT unique (OffsideGiven events can reuse another event's id), so we
            # keep it only as a reference (decision 013).
            "event_index": i,
            "source_event_id": e["id"],
            "team_event_seq": e["eventId"],
            "period": _display(e["period"]),
            "minute": e["minute"],
            "second": e.get("second"),
            "expanded_minute": e["expandedMinute"],
            "type": _display(e["type"]),
            "outcome": _display(e["outcomeType"]),
            "team_id": e["teamId"],
            "player_id": e.get("playerId"),
            "x": e["x"],
            "y": e["y"],
            "end_x": e.get("endX"),
            "end_y": e.get("endY"),
            "is_touch": e["isTouch"],
            "is_shot": e.get("isShot", False),
            "is_goal": e.get("isGoal", False),
            "is_own_goal": e.get("isOwnGoal", False),
            "card_type": _display(e["cardType"]) if "cardType" in e else None,
            "goal_mouth_y": e.get("goalMouthY"),
            "goal_mouth_z": e.get("goalMouthZ"),
            "blocked_x": e.get("blockedX"),
            "blocked_y": e.get("blockedY"),
            "related_event_id": e.get("relatedEventId"),
            "related_player_id": e.get("relatedPlayerId"),
            # Qualifiers (pass type, body part, set piece, ...) vary per event, so keep them as JSON.
            "qualifiers": json.dumps(e["qualifiers"], ensure_ascii=False),
        })

    return {"whoscored_matches": [match], "whoscored_players": players, "whoscored_events": events}


def understat_tables(path: Path) -> dict[str, list[dict]]:
    raw = read_raw(path)
    shots = [{
        "match_id": raw["match_id"],
        "season": raw["season"],
        "game": s["game"],
        "kickoff_utc": s["date"],
        "shot_id": s["shot_id"],
        "team_id": s["team_id"],
        "team": s["team"],
        "player_id": s["player_id"],
        "player": s["player"],
        "assist_player_id": s["assist_player_id"],
        "assist_player": s["assist_player"],
        "minute": s["minute"],
        "x": s["location_x"] * 100,  # Understat 0-1 -> our 0-100 convention (decision 006)
        "y": s["location_y"] * 100,
        "xg": s["xg"],
        "body_part": s["body_part"],
        "situation": s["situation"],
        "result": s["result"],
    } for s in raw["data"]["shots"]]
    return {"understat_shots": shots}


def build() -> None:
    rows: dict[str, list[dict]] = {name: [] for name in SCHEMAS}
    readers = {"whoscored": whoscored_tables, "understat": understat_tables}

    for source, reader in readers.items():
        files = sorted((RAW_DIR / source).rglob("*.json.gz"))
        for f in files:
            for table, table_rows in reader(f).items():
                rows[table].extend(table_rows)
        print(f"[{source}] read {len(files)} raw files")

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    for table, table_rows in rows.items():
        df = pd.DataFrame(table_rows)
        df = SCHEMAS[table].validate(df, lazy=True)  # lazy: report every problem, not just the first
        df.to_parquet(BRONZE_DIR / f"{table}.parquet", index=False)
        print(f"  {table}: {len(df):,} rows")


if __name__ == "__main__":
    build()
