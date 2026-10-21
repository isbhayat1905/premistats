"""premistats xG for every WhoScored shot.

A dbt Python model: it reads stg_shots, scores each shot with the base model trained by
`python -m xg.train`, then applies the Premier League calibration stage from
`python -m xg.calibrate` when it exists (decision 021). It is materialised as a table
like any SQL model, so xG sits inside the same lineage and tests as every other stat.
"""
import os
import sys
from pathlib import Path

import joblib


def model(dbt, session):
    dbt.config(materialized="table")

    root = Path(os.environ.get("PREMISTATS_ROOT", Path.cwd().parent))
    sys.path.insert(0, str(root))
    from xg.calibrate import calibration_inputs
    from xg.features import build_features

    models = root / "data" / "models"
    base = joblib.load(models / "xg_v1.joblib")
    shots = dbt.ref("stg_shots").df()

    shots["xg_base"] = base["model"].predict_proba(build_features(shots)[base["columns"]])[:, 1]
    shots["xg"] = shots["xg_base"]
    version = f"v1 base ({base['date']})"

    stage2 = models / "xg_v2_calibration.joblib"
    if stage2.exists():
        cal = joblib.load(stage2)
        shots["xg"] = cal["calibrator"].predict_proba(
            calibration_inputs(shots["xg_base"], shots["is_big_chance"]))[:, 1]
        version = f"v2 calibrated on {cal['fit_season']} ({cal['date']})"

    is_pen = shots["situation"] == "penalty"
    shots.loc[is_pen, ["xg", "xg_base"]] = base["penalty_xg"]
    shots["xg_model"] = version

    return shots[[
        "match_id", "event_index", "team_id", "player_id", "assist_player_id", "minute",
        "expanded_minute", "x", "y", "body_part", "situation", "is_big_chance", "is_shot_on_target",
        "is_goal", "xg_base", "xg", "xg_model",
    ]]
