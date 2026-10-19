"""Prototype shot map for one match, drawn from a raw Understat file.

Usage:
    Press the ▶ Run button in VS Code (draws the most recently saved match), or
    python -m analysis.shot_map data/raw/understat/2627/31248.json
"""
import json
import sys
from pathlib import Path

# Let the ▶ Run button find the `pipeline` package, which lives one folder up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch

from pipeline.config import RAW_DIR, ROOT

SURFACE = "#fcfcfb"
INK, INK_2, INK_MUTED = "#0b0b0b", "#52514e", "#8a8984"
HOME, AWAY = "#2a78d6", "#eb6834"  # categorical slots 1 & 2 (validated palette)


def load_shots(path: Path) -> pd.DataFrame:
    raw = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(raw["shots"])
    # Understat gives 0-1 coordinates with every team attacking towards x = 1.
    # Scale to 0-100 (the Opta pitch convention) and flip the home side so the
    # home team attacks left and the away team attacks right.
    df["x"] = df["location_x"] * 100
    df["y"] = df["location_y"] * 100
    home_name, away_name = teams_of(df)
    home = df["team"] == home_name
    df.loc[home, ["x", "y"]] = 100 - df.loc[home, ["x", "y"]]
    df["is_home"] = home
    df["is_goal"] = df["result"] == "Goal"
    df.attrs["teams"] = (home_name, away_name)
    return df


def teams_of(df: pd.DataFrame) -> tuple[str, str]:
    # The game label is "YYYY-MM-DD Home-Away". Match the home team against the
    # teams that shot, so names containing a hyphen still split correctly.
    label = df["game"].iloc[0].split(" ", 1)[1]
    for t in df["team"].unique():
        if label.startswith(t + "-"):
            return t, label[len(t) + 1 :]
        if label.endswith("-" + t):  # the home side had no shots at all
            return label[: -len(t) - 1], t
    raise ValueError(f"Can't match teams {df['team'].unique()} to {label!r}")


def draw(df: pd.DataFrame, out: Path) -> None:
    home_name, away_name = df.attrs["teams"]

    pitch = Pitch(pitch_type="opta", pitch_color=SURFACE, line_color="#c9c8c3", linewidth=1, pad_top=2, pad_bottom=2)
    fig, ax = pitch.draw(figsize=(11, 8.4))
    fig.set_facecolor(SURFACE)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.86, bottom=0.1)

    for is_home, colour in [(True, HOME), (False, AWAY)]:
        side = df[df.is_home == is_home]
        for is_goal in (False, True):
            s = side[side.is_goal == is_goal]
            pitch.scatter(
                s.x, s.y, ax=ax,
                s=s.xg * 1400 + 60,  # area tracks xG; floor keeps tiny chances visible
                facecolor=colour if is_goal else "none",
                edgecolor=SURFACE if is_goal else colour,
                linewidth=2, zorder=3 if is_goal else 2,
            )

    # Headline: score and xG per side, text in ink colours, colour only on the swatches.
    h, a = df[df.is_home], df[~df.is_home]
    fig.text(0.04, 0.94, f"{home_name}  {int(h.is_goal.sum())}–{int(a.is_goal.sum())}  {away_name}",
             fontsize=20, fontweight="bold", color=INK)
    fig.text(0.04, 0.9, f"xG {h.xg.sum():.2f} – {a.xg.sum():.2f}   ·   shots {len(h)} – {len(a)}   ·   "
             f"{df['date'].iloc[0][:10]}", fontsize=12, color=INK_2)

    # Legend
    handles = [
        plt.Line2D([], [], marker="o", ls="", ms=10, mfc=HOME, mec=HOME, label=f"{home_name} (attacking ←)"),
        plt.Line2D([], [], marker="o", ls="", ms=10, mfc=AWAY, mec=AWAY, label=f"{away_name} (attacking →)"),
        plt.Line2D([], [], marker="o", ls="", ms=10, mfc=INK_2, mec=INK_2, label="goal"),
        plt.Line2D([], [], marker="o", ls="", ms=10, mfc="none", mec=INK_2, mew=2, label="no goal"),
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.04, 0.025), ncol=4,
                     frameon=False, fontsize=11, labelcolor=INK_2, handletextpad=0.3, columnspacing=1.6)
    fig.text(0.96, 0.072, "marker size = xG", fontsize=11, color=INK_2, ha="right")
    fig.text(0.96, 0.035, "premistats · data: Understat", fontsize=9, color=INK_MUTED, ha="right")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:  # no file given: use the match we saved most recently
        path = max((RAW_DIR / "understat").rglob("*.json"), key=lambda p: p.stat().st_mtime)
    draw(load_shots(path), ROOT / "docs" / "img" / f"shot_map_{path.stem}.png")
