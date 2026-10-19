"""Data contracts for the bronze tables.

If a source changes its format or sends bad data, validation fails loudly here,
before anything downstream (models, charts, the website) sees it.
"""
import pandera.pandas as pa
from pandera.pandas import Check, Column

pitch = [Check.in_range(0, 100)]  # every coordinate uses the 0-100 convention (decision 006)
non_negative = [Check.ge(0)]

whoscored_matches = pa.DataFrameSchema(
    {
        "match_id": Column(int, unique=True),
        "season": Column(str),
        "kickoff_local": Column("datetime64[ns]"),
        "home_team_id": Column(int),
        "home_team": Column(str),
        "away_team_id": Column(int),
        "away_team": Column(str),
        "home_goals": Column(int, non_negative),
        "away_goals": Column(int, non_negative),
        "home_manager": Column(str, nullable=True),
        "away_manager": Column(str, nullable=True),
        "venue": Column(str, nullable=True),
        "attendance": Column("Int64", non_negative, nullable=True),
        "referee": Column(str, nullable=True),
        "max_minute_expanded": Column(int, Check.in_range(90, 140)),
        "fetched_at": Column(str),
    },
    checks=Check(lambda df: (df.home_team_id != df.away_team_id).all(), error="team plays itself"),
    coerce=True,
    strict=True,
)

whoscored_players = pa.DataFrameSchema(
    {
        "match_id": Column(int),
        "team_id": Column(int),
        "player_id": Column(int),
        "player": Column(str),
        "shirt_no": Column("Int64", nullable=True),
        "position": Column(str, nullable=True),
        "is_starter": Column(bool),
        "subbed_in_minute": Column("Int64", non_negative, nullable=True),
        "subbed_out_minute": Column("Int64", non_negative, nullable=True),
        "age": Column("Int64", Check.in_range(15, 45), nullable=True),
        "height_cm": Column("Int64", Check.in_range(150, 210), nullable=True),
    },
    unique=["match_id", "player_id"],
    checks=Check(lambda df: df.groupby(["match_id", "team_id"]).is_starter.sum().eq(11).all(),
                 error="every team should name exactly 11 starters"),
    coerce=True,
    strict=True,
)

whoscored_events = pa.DataFrameSchema(
    {
        "match_id": Column(int),
        "event_index": Column(int, Check.ge(0)),
        "source_event_id": Column(int),
        "team_event_seq": Column(int),
        "period": Column(str),
        "minute": Column(int, non_negative),
        "second": Column("Int64", Check.in_range(0, 59), nullable=True),
        "expanded_minute": Column(int, non_negative),
        "type": Column(str),
        "outcome": Column(str, Check.isin(["Successful", "Unsuccessful"])),
        "team_id": Column(int),
        "player_id": Column("Int64", nullable=True),
        "x": Column(float, pitch),
        "y": Column(float, pitch),
        "end_x": Column(float, pitch, nullable=True),
        "end_y": Column(float, pitch, nullable=True),
        "is_touch": Column(bool),
        "is_shot": Column(bool),
        "is_goal": Column(bool),
        "is_own_goal": Column(bool),
        "card_type": Column(str, nullable=True),
        "goal_mouth_y": Column(float, nullable=True),
        "goal_mouth_z": Column(float, nullable=True),
        "blocked_x": Column(float, pitch, nullable=True),
        "blocked_y": Column(float, pitch, nullable=True),
        "related_event_id": Column("Int64", nullable=True),
        "related_player_id": Column("Int64", nullable=True),
        "qualifiers": Column(str),
    },
    unique=["match_id", "event_index"],
    coerce=True,
    strict=True,
)

understat_shots = pa.DataFrameSchema(
    {
        "match_id": Column(int),
        "season": Column(str),
        "game": Column(str),
        "kickoff_utc": Column("datetime64[ns]"),
        "shot_id": Column(int, unique=True),
        "team_id": Column(int),
        "team": Column(str),
        "player_id": Column(int),
        "player": Column(str),
        "assist_player_id": Column("Int64", nullable=True),
        "assist_player": Column(str, nullable=True),
        "minute": Column(int, Check.in_range(0, 130)),
        "x": Column(float, pitch),
        "y": Column(float, pitch),
        "xg": Column(float, Check.in_range(0, 1)),
        "body_part": Column(str, nullable=True),
        "situation": Column(str, nullable=True),
        "result": Column(str),
    },
    coerce=True,
    strict=True,
)

SCHEMAS = {
    "whoscored_matches": whoscored_matches,
    "whoscored_players": whoscored_players,
    "whoscored_events": whoscored_events,
    "understat_shots": understat_shots,
}
