"""premistats xG for every WhoScored shot.

A dbt Python model: it reads stg_shots, scores each shot with the model trained by
`python -m xg.train`, and is materialised as a table like any SQL model, so xG sits
inside the same lineage and tests as every other stat.
"""
import os
import sys
from pathlib import Path

import joblib


def model(dbt, session):
    dbt.config(materialized="table")

    root = Path(os.environ.get("PREMISTATS_ROOT", Path.cwd().parent))
    sys.path.insert(0, str(root))
    from xg.features import build_features

    bundle = joblib.load(root / "data" / "models" / "xg_v1.joblib")
    shots = dbt.ref("stg_shots").df()

    features = build_features(shots)[bundle["columns"]]
    shots["xg"] = bundle["model"].predict_proba(features)[:, 1]
    shots.loc[shots["situation"] == "penalty", "xg"] = bundle["penalty_xg"]
    shots["xg_model"] = f"{bundle['name']} ({bundle['date']})"

    return shots[[
        "match_id", "event_index", "team_id", "player_id", "assist_player_id", "minute",
        "expanded_minute", "x", "y", "body_part", "situation", "is_big_chance", "is_shot_on_target",
        "is_goal", "xg", "xg_model",
    ]]
