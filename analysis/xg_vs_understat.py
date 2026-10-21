"""Validate premistats xG against Understat's xG on 2026/27 Premier League matches.

Two independent models from two independent data providers: if they agree on each
team's xG per match, our model has transferred well from its training data.

Usage:
    Press ▶ Run, or python -m analysis.xg_vs_understat
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import matplotlib.pyplot as plt
import numpy as np

from pipeline.config import CURRENT_SEASON, DATA_DIR, ROOT

SURFACE = "#fcfcfb"
INK, INK_2, INK_MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
DOT = "#2a78d6"

QUERY = """
with ours as (
    select m.match_id, m.match_date, t.team, sum(s.xg) as xg, count(*) as shots, sum(s.is_goal::int) as goals
    from silver.shot_xg s
    join silver.stg_matches m using (match_id)
    join (select match_id, home_team_id as team_id, home_team as team from silver.stg_matches
          union all select match_id, away_team_id, away_team from silver.stg_matches) t using (match_id, team_id)
    where m.season = '{season}'
    group by all
),
theirs as (
    select match_date, team, sum(xg) as xg, count(*) as shots
    from silver.stg_understat_shots
    where season = '{season}'
    group by all
)
select o.match_id, o.match_date, o.team, o.goals, o.shots, u.shots as u_shots, o.xg, u.xg as u_xg
from ours o
join theirs u on u.team = o.team and u.match_date = o.match_date
"""


def main() -> None:
    con = duckdb.connect(str(DATA_DIR / "warehouse.duckdb"), read_only=True)
    df = con.sql(QUERY.format(season=CURRENT_SEASON)).df()
    season = df.groupby("team")[["goals", "xg", "u_xg"]].sum()
    con.close()

    r_match = np.corrcoef(df.xg, df.u_xg)[0, 1]
    r_team = np.corrcoef(season.xg, season.u_xg)[0, 1]
    mae = (df.xg - df.u_xg).abs().mean()
    ratio = df.xg.sum() / df.u_xg.sum()
    print(f"Team-matches compared: {len(df)} (shots: ours {df.shots.sum()}, Understat {df.u_shots.sum()})")
    print(f"Correlation per team-match: r = {r_match:.3f}   mean abs difference = {mae:.3f} xG")
    print(f"Correlation per team-season: r = {r_team:.3f}")
    print(f"Total xG: ours {df.xg.sum():.1f}, Understat {df.u_xg.sum():.1f} (ratio {ratio:.3f}); goals {df.goals.sum()}")
    print(season.sort_values("xg", ascending=False).round(1).to_string())

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    fig.subplots_adjust(left=0.11, right=0.96, top=0.85, bottom=0.1)
    lim = max(df.xg.max(), df.u_xg.max()) * 1.05
    ax.plot([0, lim], [0, lim], color=GRID, lw=1.5, zorder=1)
    ax.scatter(df.u_xg, df.xg, s=46, color=DOT, edgecolor=SURFACE, linewidth=1.2, alpha=0.85, zorder=2)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_aspect("equal")
    ax.set_xlabel("Understat xG", fontsize=12, color=INK_2)
    ax.set_ylabel("premistats xG", fontsize=12, color=INK_2)
    ax.tick_params(colors=INK_MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    fig.text(0.11, 0.94, "premistats xG vs Understat xG", fontsize=17, fontweight="bold", color=INK)
    fig.text(0.11, 0.9, f"Each dot is one team in one match, PL 2026/27 ({len(df)} team-matches) · "
             f"r = {r_match:.2f}", fontsize=10.5, color=INK_2)
    fig.text(0.96, 0.02, "premistats · data: WhoScored, Understat; model trained on StatsBomb open data",
             fontsize=8, color=INK_MUTED, ha="right")
    out = ROOT / "docs" / "img" / "xg_vs_understat.png"
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
