"""Train and evaluate premistats xG on StatsBomb open data.

Three candidates are compared on the same held-out matches:
  1. baseline: logistic regression on distance + angle only
  2. logistic: logistic regression on all shared features
  3. boosted:  gradient-boosted trees on all shared features
plus StatsBomb's own xG as a benchmark. Penalties are left out of the model and get
a fixed xG equal to the penalty conversion rate in the training data.

Outputs: the chosen model (data/models/), a model card (docs/xg_model.md) and charts.

Usage:
    python -m xg.train
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pipeline.config import DATA_DIR, ROOT
from xg.features import build_features, from_statsbomb

MODEL_DIR = DATA_DIR / "models"
IMG_DIR = ROOT / "docs" / "img"
SEED = 19

SURFACE = "#fcfcfb"
INK, INK_2, INK_MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
SERIES = {"baseline": "#eda100", "logistic": "#1baf7a", "boosted": "#2a78d6", "statsbomb": "#eb6834"}
FEATURE_LABELS = {
    "angle_rad": "Angle to goal", "distance_m": "Distance (m)", "log_distance": "Distance (log)",
    "distance_x_header": "Header × distance", "body_head": "Header", "body_other": "Other body part",
    "first_time": "First-time shot", "one_on_one": "One-on-one", "volley": "Volley",
    "assisted": "Assisted", "assist_cross": "From a cross", "assist_through_ball": "From a through ball",
    "sit_counter": "Counter-attack", "sit_corner": "From a corner", "sit_set_piece_other": "Other set piece",
    "sit_free_kick_direct": "Direct free kick",
}
LABELS = {"baseline": "Baseline (distance + angle)", "logistic": "Logistic regression",
          "boosted": "Gradient boosting", "statsbomb": "StatsBomb xG (benchmark)"}


def load():
    sb = pd.read_parquet(DATA_DIR / "external" / "statsbomb" / "shots.parquet")
    common = from_statsbomb(sb)
    X = build_features(common)
    y = sb["is_goal"].astype(int)
    return sb, common, X, y


def make_models():
    return {
        "baseline": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "boosted": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=80,
            l2_regularization=1.0, early_stopping=True, random_state=SEED,
        ),
    }


def score(y, p) -> dict:
    return {"log_loss": log_loss(y, p), "brier": brier_score_loss(y, p), "roc_auc": roc_auc_score(y, p),
            "mean_xg": float(np.mean(p)), "goal_rate": float(np.mean(y))}


def plot_calibration(y, preds: dict, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 7.4))
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.84, bottom=0.2)
    ax.plot([0, 1], [0, 1], color=GRID, lw=1.5, zorder=1)
    ax.text(0.36, 0.385, "perfect calibration", rotation=41, color=INK_MUTED, fontsize=9)
    for name, p in preds.items():
        frac, mean_pred = calibration_curve(y, p, n_bins=12, strategy="quantile")
        ax.plot(mean_pred, frac, color=SERIES[name], lw=2, marker="o", ms=6, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=LABELS[name])
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 0.5)
    ax.set_xlabel("Predicted xG", fontsize=12, color=INK_2)
    ax.set_ylabel("Actual goal rate", fontsize=12, color=INK_2)
    ax.tick_params(colors=INK_MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    fig.legend(loc="lower left", bbox_to_anchor=(0.1, 0.02), ncol=2, frameon=False, fontsize=10,
               labelcolor=INK_2)
    fig.text(0.11, 0.93, "xG calibration on held-out matches", fontsize=17, fontweight="bold", color=INK)
    fig.text(0.11, 0.89, "Shots grouped into 12 equal-size bins. On the diagonal = predicted xG matches reality.",
             fontsize=10.5, color=INK_2)
    fig.text(0.97, 0.005, "premistats · data: StatsBomb open data", fontsize=8, color=INK_MUTED, ha="right")
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_importance(imp: pd.Series, out: Path) -> None:
    imp = imp.sort_values().rename(index=FEATURE_LABELS)
    fig, ax = plt.subplots(figsize=(8, 6.4))
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    fig.subplots_adjust(left=0.3, right=0.95, top=0.83, bottom=0.1)
    ax.barh(imp.index, imp.values, color=SERIES["boosted"], height=0.62, zorder=2)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    ax.set_xlabel("Increase in log loss when the feature is shuffled", fontsize=11, color=INK_2)
    ax.tick_params(colors=INK_2, labelsize=10)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    fig.text(0.03, 0.93, "What drives the xG model", fontsize=17, fontweight="bold", color=INK)
    fig.text(0.03, 0.885, "Permutation importance on held-out matches (gradient boosting)", fontsize=10.5,
             color=INK_2)
    fig.text(0.95, 0.01, "premistats · data: StatsBomb open data", fontsize=8, color=INK_MUTED, ha="right")
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def write_model_card(results: pd.DataFrame, per_comp: pd.DataFrame, penalty_xg: float, n: dict,
                     chosen: str, out: Path) -> None:
    fmt = results.copy()
    fmt.index = [LABELS[i] for i in fmt.index]
    lines = [
        "# premistats xG model card",
        "",
        f"*Generated by `python -m xg.train` on {date.today():%d %b %Y}. Do not edit by hand.*",
        "",
        "## What it is",
        "Expected goals (xG) is the probability that a shot becomes a goal, based on where it was taken "
        "and how. premistats trains its own model on StatsBomb open data and applies it to every 2026/27 "
        "Premier League shot recorded by WhoScored.",
        "",
        "## Training data",
        f"- **{n['shots']:,} non-penalty shots** from **{n['matches']:,} matches**: four complete 2015/16 "
        "top-flight seasons (England, Spain, Italy, France), World Cups 2018 and 2022, and Euros 2020 and 2024. "
        "One-club samples are excluded (decision 017).",
        f"- Split **by match** (80/20): {n['train']:,} training shots, {n['test']:,} test shots. Shots from the same "
        "match never appear on both sides, which keeps match-level patterns from leaking into the test set.",
        f"- **Penalties** are left out of the model and get a fixed xG of **{penalty_xg:.2f}**, the penalty "
        "conversion rate in the training data.",
        "",
        "## Features",
        "Only features both StatsBomb and WhoScored record, mapped to one shared vocabulary "
        "(`xg/features.py`): distance and goal angle, body part, situation (open play, counter, corner, "
        "other set piece, direct free kick), first-time, one-on-one, volley, and whether the shot was "
        "assisted, from a cross or from a through ball.",
        "",
        "## Results on held-out matches",
        "Lower log loss and Brier score are better; higher ROC AUC is better.",
        "",
        "| Model | Log loss | Brier | ROC AUC | Mean xG | Goal rate |",
        "|---|---|---|---|---|---|",
        *[f"| {i} | {r.log_loss:.4f} | {r.brier:.4f} | {r.roc_auc:.3f} | {r.mean_xg:.3f} | {r.goal_rate:.3f} |"
          for i, r in fmt.iterrows()],
        "",
        f"**Chosen model: {LABELS[chosen]}** (lowest log loss of our models).",
        "",
        "StatsBomb's own xG also uses information we can't (defender and goalkeeper positions at the moment "
        "of the shot), so it is an upper benchmark rather than a like-for-like competitor.",
        "",
        "### By competition (chosen model, test set)",
        "",
        "| Competition | Shots | Goals | Sum of xG | Log loss |",
        "|---|---|---|---|---|",
        *[f"| {c} | {int(r.shots):,} | {int(r.goals):,} | {r.xg:.1f} | {r.log_loss:.4f} |" for c, r in per_comp.iterrows()],
        "",
        "![Calibration](img/xg_calibration.png)",
        "",
        "![Feature importance](img/xg_importance.png)",
        "",
        "## Known limitations",
        "- No defender or goalkeeper positions (WhoScored doesn't publish them), so a shot through a crowd "
        "and an open-goal tap-in from the same spot get similar xG.",
        "- Training data is mostly 2015/16; finishing and shot selection have shifted slightly since.",
        "- Situation labels come from two providers with slightly different definitions (decision 018).",
        "",
        "Data: StatsBomb open data, used under the StatsBomb Public Data User Agreement.",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    sb, common, X, y = load()
    is_pen = common["situation"] == "penalty"
    penalty_xg = float(y[is_pen].mean())
    X, y, sb = X[~is_pen], y[~is_pen], sb[~is_pen]

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    train_idx, test_idx = next(splitter.split(X, y, groups=sb["match_id"]))
    X_tr, X_te, y_tr, y_te = X.iloc[train_idx], X.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx]

    models = make_models()
    baseline_cols = ["distance_m", "angle_rad", "log_distance"]
    preds, results = {}, {}
    for name, model in models.items():
        cols = baseline_cols if name == "baseline" else list(X.columns)
        model.fit(X_tr[cols], y_tr)
        preds[name] = model.predict_proba(X_te[cols])[:, 1]
        results[name] = score(y_te, preds[name])
    preds["statsbomb"] = sb["statsbomb_xg"].iloc[test_idx].to_numpy()
    results["statsbomb"] = score(y_te, preds["statsbomb"])
    results = pd.DataFrame(results).T

    chosen = results.drop("statsbomb")["log_loss"].idxmin()
    print(results.round(4).to_string())
    print(f"Chosen: {chosen}")

    test = sb.iloc[test_idx].assign(xg=preds[chosen], goal=y_te.to_numpy())
    per_comp = test.groupby("competition").apply(
        lambda g: pd.Series({"shots": len(g), "goals": int(g.goal.sum()), "xg": g.xg.sum(),
                             "log_loss": log_loss(g.goal, g.xg, labels=[0, 1])}),
        include_groups=False,
    )

    imp = permutation_importance(models["boosted"], X_te, y_te, scoring="neg_log_loss",
                                 n_repeats=5, random_state=SEED)
    importance = pd.Series(imp.importances_mean, index=X.columns)

    # Refit the chosen model on all shots before saving: the test split has done its job.
    final = make_models()[chosen]
    cols = baseline_cols if chosen == "baseline" else list(X.columns)
    final.fit(X[cols], y)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": final, "columns": cols, "penalty_xg": penalty_xg, "name": chosen,
                 "trained_on": f"{len(X):,} StatsBomb open-data shots", "date": date.today().isoformat()},
                MODEL_DIR / "xg_v1.joblib")

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    plot_calibration(y_te, preds, IMG_DIR / "xg_calibration.png")
    plot_importance(importance, IMG_DIR / "xg_importance.png")
    n = {"shots": len(X), "matches": sb["match_id"].nunique(), "train": len(train_idx), "test": len(test_idx)}
    write_model_card(results, per_comp, penalty_xg, n, chosen, ROOT / "docs" / "xg_model.md")
    (MODEL_DIR / "xg_v1_metrics.json").write_text(results.to_json(indent=1), encoding="utf-8")
    print("Saved model, docs/xg_model.md and charts")


if __name__ == "__main__":
    main()
