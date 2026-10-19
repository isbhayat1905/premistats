"""The contract every data source must follow.

Downstream code only talks to this interface, never to a specific website.
If a source breaks or blocks us, we write a new adapter and nothing else changes.
"""
from typing import Protocol

import pandas as pd


class ShotSource(Protocol):
    name: str

    def list_matches(self, season: str) -> pd.DataFrame:
        """One row per fixture: match_id, date, home_team, away_team, is_result."""
        ...

    def get_match_shots(self, season: str, match_id: int) -> list[dict]:
        """Raw shot records for one match, exactly as the source gives them."""
        ...
