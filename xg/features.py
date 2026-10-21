"""Shot features shared by training (StatsBomb) and scoring (WhoScored).

Both sources are first converted to one common table (see COMMON_COLUMNS), and
every feature is computed from that table by the same function, `build_features`.
This guarantees the model sees exactly the same inputs at training and scoring time.
"""
import numpy as np
import pandas as pd

# Common shot table: coordinates on the 0-100 scale, shooter attacking towards x = 100.
COMMON_COLUMNS = [
    "x", "y", "body_part", "situation", "first_time", "one_on_one", "volley",
    "assisted", "assist_cross", "assist_through_ball",
]
BODY_PARTS = ["foot", "head", "other"]
SITUATIONS = ["open_play", "counter", "corner", "set_piece_other", "free_kick_direct", "penalty"]

PITCH_LENGTH_M, PITCH_WIDTH_M, GOAL_WIDTH_M = 105.0, 68.0, 7.32


def from_statsbomb(sb: pd.DataFrame) -> pd.DataFrame:
    """Map raw StatsBomb shots (xg/statsbomb.py) onto the common table."""
    def situation(r) -> str:
        if r.shot_type == "Penalty":
            return "penalty"
        if r.shot_type == "Free Kick":
            return "free_kick_direct"
        return {
            "From Corner": "corner",
            "From Free Kick": "set_piece_other",
            "From Throw In": "set_piece_other",
            "From Counter": "counter",
        }.get(r.play_pattern, "open_play")

    out = pd.DataFrame({
        "x": sb["x"] / 1.2,  # 120 x 80 -> 0-100
        "y": sb["y"] / 0.8,
        "body_part": sb["body_part"].map({"Head": "head", "Other": "other"}).fillna("foot"),
        "situation": sb.apply(situation, axis=1),
        "first_time": sb["first_time"],
        "one_on_one": sb["one_on_one"],
        "volley": sb["technique"].isin(["Volley", "Half Volley"]),
        "assisted": sb["assisted"],
        "assist_cross": sb["assist_cross"],
        "assist_through_ball": sb["assist_through_ball"],
    })
    return out


def build_features(shots: pd.DataFrame) -> pd.DataFrame:
    """Numeric model inputs from the common shot table."""
    dx = (100 - shots["x"]) * PITCH_LENGTH_M / 100
    dy = (shots["y"] - 50).abs() * PITCH_WIDTH_M / 100
    distance = np.hypot(dx, dy)
    # Angle the goal mouth subtends from the shot location (bigger = more of the goal to aim at).
    half = GOAL_WIDTH_M / 2
    angle = np.arctan2(GOAL_WIDTH_M * dx, dx ** 2 + dy ** 2 - half ** 2)
    angle = np.where(angle < 0, angle + np.pi, angle)

    f = pd.DataFrame({
        "distance_m": distance,
        "angle_rad": angle,
        "log_distance": np.log1p(distance),
        "distance_x_header": distance * (shots["body_part"] == "head"),
        "first_time": shots["first_time"].astype(int),
        "one_on_one": shots["one_on_one"].astype(int),
        "volley": shots["volley"].astype(int),
        "assisted": shots["assisted"].astype(int),
        "assist_cross": shots["assist_cross"].astype(int),
        "assist_through_ball": shots["assist_through_ball"].astype(int),
    }, index=shots.index)
    for b in BODY_PARTS[1:]:  # foot is the baseline
        f[f"body_{b}"] = (shots["body_part"] == b).astype(int)
    for s in SITUATIONS[1:-1]:  # open play is the baseline; penalties are handled outside the model
        f[f"sit_{s}"] = (shots["situation"] == s).astype(int)
    return f
