"""WhoScored adapter: full event data (every on-ball action with x/y), lineups and formations.

WhoScored sits behind bot protection, so soccerdata drives a real (headless)
Chrome browser. That makes it slow (~10 s per match) and it only works from a
home connection, not from cloud CI.
"""
import json

import pandas as pd

import pipeline.config  # noqa: F401  (sets the soccerdata cache dir before import)
import soccerdata as sd

LEAGUE = "ENG-Premier League"
STATUS_FINISHED = 6


class WhoScoredSource:
    name = "whoscored"

    def __init__(self) -> None:
        self._clients: dict[str, sd.WhoScored] = {}

    def _client(self, season: str) -> sd.WhoScored:
        # Starting the browser is slow, so reuse one per season for the whole run.
        if season not in self._clients:
            self._clients[season] = sd.WhoScored(leagues=LEAGUE, seasons=season, headless=True)
        return self._clients[season]

    def list_matches(self, season: str) -> pd.DataFrame:
        s = self._client(season).read_schedule().reset_index()
        s["is_result"] = s["status"] == STATUS_FINISHED
        return s.rename(columns={"game_id": "match_id", "home_score": "home_goals", "away_score": "away_goals"})[
            ["match_id", "date", "home_team", "away_team", "home_goals", "away_goals", "is_result"]
        ]

    def get_match(self, season: str, match_id: int) -> dict:
        client = self._client(season)
        # output_fmt=None just downloads and caches the page; we then keep the
        # complete match-centre JSON (events + lineups + formations), not
        # soccerdata's trimmed-down events table.
        # force_cache=True stops soccerdata re-downloading the 10-page fixture list
        # for every single match (list_matches already fetched a fresh copy). This
        # took a match from ~107 s to a few seconds.
        client.read_events(match_id=match_id, output_fmt=None, force_cache=True)
        cached = next(client.data_dir.glob(f"events/*_{season}/{match_id}.json"))
        data = json.loads(cached.read_text(encoding="utf-8"))
        if not data or "events" not in data:
            raise ValueError(f"WhoScored returned no events for match {match_id}")
        return data
