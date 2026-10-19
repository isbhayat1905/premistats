"""The contract every data source must follow.

Downstream code only talks to this interface, never to a specific website.
If a source breaks or blocks us, we write a new adapter and nothing else changes.
"""
from typing import Protocol

import pandas as pd


class Source(Protocol):
    name: str

    def list_matches(self, season: str) -> pd.DataFrame:
        """One row per fixture with at least: match_id, date, home_team, away_team, is_result."""
        ...

    def get_match(self, season: str, match_id: int) -> dict:
        """Everything the source has for one match, exactly as the source gives it."""
        ...
