"""Prototype of the X/Y chart builder: any two player stats against each other.

Usage:
    Press ▶ Run (progressive passes vs chances created, per 90), or
    python -m analysis.scatter touches_in_box_p90 shots_p90 --min-minutes 450
    python -m analysis.scatter --list          # show every stat you can plot
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import matplotlib.pyplot as plt
from adjustText import adjust_text

from pipeline.config import CURRENT_SEASON, DATA_DIR, ROOT

SURFACE = "#fcfcfb"
INK, INK_2, INK_MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e6e5e0"
DOT = "#2a78d6"
SKIP = {"season", "player_id", "player", "team", "position"}


def load(min_minutes: int):
    con = duckdb.connect(str(DATA_DIR / "warehouse.duckdb"), read_only=True)
    df = con.sql(f"select * from gold.player_season_stats "
                 f"where season = '{CURRENT_SEASON}' and minutes >= {min_minutes}").df()
    con.close()
    return df


ACRONYMS = {"Xg": "xG", "Npxg": "npxG", "Xa": "xA", "xg": "xG", "npxg": "npxG", "xa": "xA"}


def pretty(col: str) -> str:
    words = col.replace("_p90", " per 90").replace("_", " ").capitalize().split()
    return " ".join(ACRONYMS.get(w, w) for w in words)


def credit(x: str, y: str) -> str:
    # StatsBomb's licence requires credit on anything published from their data (decision 017).
    uses_xg = any(k in c for c in (x, y) for k in ("xg", "xa"))
    return "premistats · data: WhoScored" + (" · xG model trained on StatsBomb open data" if uses_xg else "")


def draw(df, x: str, y: str, min_minutes: int, n_labels: int, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 8))
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.1)

    # Recessive reference lines at the median so "above average" is easy to read.
    ax.axvline(df[x].median(), color=GRID, lw=1.5, zorder=1)
    ax.axhline(df[y].median(), color=GRID, lw=1.5, zorder=1)
    ax.scatter(df[x], df[y], s=60, color=DOT, edgecolor=SURFACE, linewidth=1.5, alpha=0.85, zorder=2)

    # Label only the standouts: furthest from the median on both axes combined.
    z = ((df[x] - df[x].median()) / df[x].std()) ** 2 + ((df[y] - df[y].median()) / df[y].std()) ** 2
    labels = [ax.text(r[x], r[y], r["player"], fontsize=10, color=INK_2, zorder=3)
              for _, r in df.loc[z.nlargest(n_labels).index].iterrows()]
    # Leave room for labels at the edges, then let adjustText push overlapping labels apart.
    ax.margins(x=0.12, y=0.08)
    adjust_text(labels, ax=ax, x=df[x].to_numpy(), y=df[y].to_numpy(),
                arrowprops=dict(arrowstyle="-", color=INK_MUTED, lw=0.6))

    ax.set_xlabel(pretty(x), fontsize=12, color=INK_2)
    ax.set_ylabel(pretty(y), fontsize=12, color=INK_2)
    ax.tick_params(colors=INK_MUTED, labelsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)

    fig.text(0.08, 0.94, f"{pretty(x)} vs {pretty(y)}", fontsize=20, fontweight="bold", color=INK)
    fig.text(0.08, 0.905, f"Premier League 2026/27 · players with {min_minutes}+ minutes ({len(df)}) · "
             "lines show the median", fontsize=12, color=INK_2)
    fig.text(0.97, 0.02, credit(x, y), fontsize=9, color=INK_MUTED, ha="right")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("x", nargs="?", default="progressive_passes_p90")
    parser.add_argument("y", nargs="?", default="chances_created_p90")
    parser.add_argument("--min-minutes", type=int, default=450)
    parser.add_argument("--labels", type=int, default=10)
    parser.add_argument("--list", action="store_true", help="list plottable stats")
    args = parser.parse_args()

    df = load(args.min_minutes)
    stats = [c for c in df.columns if c not in SKIP]
    if args.list:
        print("\n".join(stats))
        return
    for col in (args.x, args.y):
        if col not in stats:
            sys.exit(f"Unknown stat {col!r}. Run with --list to see them all.")

    slug = re.sub(r"[^a-z0-9]+", "-", f"{args.x}-vs-{args.y}")
    draw(df, args.x, args.y, args.min_minutes, args.labels, ROOT / "docs" / "img" / f"scatter_{slug}.png")


if __name__ == "__main__":
    main()
