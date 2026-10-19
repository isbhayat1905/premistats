"""Understat adapter: shot-level data (location, xG, outcome) via the soccerdata library."""
import pandas as pd

import pipeline.config  # noqa: F401  (sets the soccerdata cache dir before import)
import soccerdata as sd

LEAGUE = "ENG-Premier League"


class UnderstatSource:
    name = "understat"

    def _client(self, season: str) -> sd.Understat:
        # soccerdata caches every response on disk, so re-runs don't hit the site again.
        return sd.Understat(leagues=LEAGUE, seasons=season)

    def list_matches(self, season: str) -> pd.DataFrame:
        s = self._client(season).read_schedule().reset_index()
        return s.rename(columns={"game_id": "match_id"})[
            ["match_id", "date", "home_team", "away_team", "home_goals", "away_goals", "is_result"]
        ]

    def get_match(self, season: str, match_id: int) -> dict:
        shots = self._client(season).read_shot_events(match_id=match_id).reset_index()
        # JSON can't hold pandas timestamps or NA, so convert them to plain values.
        shots["date"] = shots["date"].astype(str)
        shots = shots.astype(object).where(shots.notna(), None)
        return {"shots": shots.to_dict(orient="records")}
