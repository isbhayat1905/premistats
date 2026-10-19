"""Touch map + heatmap for one player in one match, from a raw WhoScored file.

Usage:
    Press ▶ Run (latest match, player with the most touches), or
    python -m analysis.player_touches data/raw/whoscored/2627/1983614.json.gz "Declan Rice"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch

from pipeline.config import RAW_DIR, ROOT
from pipeline.raw import read_raw

SURFACE = "#fcfcfb"
INK, INK_2, INK_MUTED = "#0b0b0b", "#52514e", "#8a8984"
LINE = "#c9c8c3"
TOUCH = "#2a78d6"
# Sequential blue ramp (palette steps 100 -> 700), starting from the surface so empty zones recede.
HEAT = LinearSegmentedColormap.from_list(
    "heat", [SURFACE, "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)


def load_touches(path: Path) -> tuple[pd.DataFrame, dict]:
    match = read_raw(path)["data"]
    names = {int(k): v for k, v in match["playerIdNameDictionary"].items()}
    teams = {match[side]["teamId"]: match[side]["name"] for side in ("home", "away")}
    ev = pd.DataFrame(match["events"])
    # WhoScored (Opta) coordinates are already 0-100 with each team attacking towards x = 100.
    touches = ev[ev["isTouch"] & ev["playerId"].notna()].copy()
    touches["player"] = touches["playerId"].astype(int).map(names)
    touches["team"] = touches["teamId"].map(teams)
    info = {
        "home": match["home"]["name"],
        "away": match["away"]["name"],
        "score": match["ftScore"].replace(" : ", "–"),
        "date": match["startDate"][:10],
    }
    return touches[["player", "team", "minute", "x", "y"]], info


def draw(touches: pd.DataFrame, info: dict, player: str, out: Path) -> None:
    t = touches[touches["player"] == player]
    if t.empty:
        raise ValueError(f"No touches for {player!r}. Players: {sorted(touches['player'].unique())}")

    pitch = Pitch(pitch_type="opta", pitch_color=SURFACE, line_color=LINE, linewidth=1, line_zorder=2)
    # grid() reserves fixed bands for the title and footer so text never overlaps the pitches.
    fig, grid = pitch.grid(nrows=1, ncols=2, figheight=7.4, grid_height=0.7, title_height=0.13,
                           endnote_height=0.08, space=0.05, axis=False)
    axs = grid["pitch"]
    fig.set_facecolor(SURFACE)

    # Left: every touch as a dot.
    pitch.scatter(t.x, t.y, ax=axs[0], s=70, facecolor=TOUCH, edgecolor=SURFACE, linewidth=1.5, zorder=3)

    # Right: touches counted in a 6 x 5 grid of zones.
    stats = pitch.bin_statistic(t.x, t.y, statistic="count", bins=(6, 5))
    pitch.heatmap(stats, ax=axs[1], cmap=HEAT, edgecolor=SURFACE, linewidth=2, zorder=1)
    # Label each zone with its count; dark zones get light text so it stays readable.
    peak = stats["statistic"].max()
    for count, cx, cy in zip(stats["statistic"].flat, stats["cx"].flat, stats["cy"].flat):
        if count > 0:
            pitch.annotate(f"{count:.0f}", xy=(cx, cy), ax=axs[1], ha="center", va="center", fontsize=11,
                           color=SURFACE if count > 0.55 * peak else INK_2, zorder=3)

    for ax, title in zip(axs, ["Every touch", "Touches per zone"]):
        ax.set_title(title, loc="left", fontsize=13, color=INK_2, pad=8)
        ax.annotate("", xy=(62, -4), xytext=(38, -4), annotation_clip=False,
                    arrowprops=dict(arrowstyle="->", color=INK_MUTED, lw=1.2))
        ax.text(50, -8.5, "attacking direction", ha="center", fontsize=10, color=INK_MUTED)

    team = t["team"].iloc[0]
    title, endnote = grid["title"], grid["endnote"]
    title.text(0, 0.75, player, fontsize=22, fontweight="bold", color=INK, va="center")
    title.text(0, 0.25, f"{team}  ·  {info['home']} {info['score']} {info['away']}  ·  {info['date']}  ·  "
               f"{len(t)} touches", fontsize=12, color=INK_2, va="center")
    endnote.text(1, 0.3, "premistats · data: WhoScored", fontsize=9, color=INK_MUTED, ha="right")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:  # no file given: use the match we saved most recently
        path = max((RAW_DIR / "whoscored").rglob("*.json.gz"), key=lambda p: p.stat().st_mtime)
    touches, info = load_touches(path)
    player = sys.argv[2] if len(sys.argv) > 2 else touches["player"].value_counts().index[0]
    slug = re.sub(r"[^a-z0-9]+", "-", player.lower()).strip("-")
    draw(touches, info, player, ROOT / "docs" / "img" / f"touches_{path.name.split('.')[0]}_{slug}.png")
