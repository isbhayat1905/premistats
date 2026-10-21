# Metric definitions

Exactly how each stat is calculated, so numbers can be checked and compared with
other sites. SQL lives in [dbt/models](../dbt/models).

**Coordinates:** 0–100 on both axes, each team attacking towards x = 100. y = 0 is the
right touchline from the attacker's view. Distances in metres assume a 105 × 68 m pitch.

## Playing time
| Metric | Definition |
|---|---|
| Minutes | Time on the pitch using WhoScored's *expanded* minute, which includes stoppage time, so a full match is often 95–100. Starters begin at 0, subs at their entry minute. Players stop at their substitution, a red card, or full time. A sub brought on in the final minute can have 0 minutes: they still count as an appearance. |
| Per 90 (`_p90`) | `count × 90 / minutes`. Be careful with small samples: compare players with at least ~450 minutes. |

## Passing
| Metric | Definition |
|---|---|
| Passes / completed | All `Pass` events / those with outcome `Successful`. |
| Open-play pass | A pass that is **not** a corner, free kick, throw-in, goal kick or keeper throw. |
| Progressive pass | A completed open-play pass that starts at x ≥ 40 and ends at least **25% closer** to the centre of the opponent's goal. |
| Pass into box | A completed pass from outside the penalty area to inside it, excluding corners. |
| Cross / long ball / through ball | Pass carrying WhoScored's `Cross` / `Longball` / `Throughball` qualifier. |
| Chance created | Pass tagged `KeyPass` (led to a shot) or `IntentionalGoalAssist` (led to a goal). |
| Assist | Pass tagged `IntentionalGoalAssist`. |

## Shooting
| Metric | Definition |
|---|---|
| Shot | Event with `isShot`, excluding own goals. |
| On target | Goals, plus saved shots that were not blocked by an outfield player. |
| Non-penalty goals | Goals without the `Penalty` qualifier. |
| Touches in box | Touch events starting inside the penalty area (x ≥ 83, 21.1 ≤ y ≤ 78.9). |

## Expected goals
Full details, results and limitations: [xg_model.md](xg_model.md). Model trained on StatsBomb open data.

| Metric | Definition |
|---|---|
| xG | Probability a shot is scored, from premistats' own model (`silver.shot_xg`). Penalties = 0.73. |
| npxG | xG excluding penalties. |
| xA | xG of the shots a player set up with a pass (the pass linked to the shot by WhoScored). |
| Goals minus xG | Goals − xG. Positive = finishing above expectation (or luck, in small samples). |
| npxG per shot | npxG ÷ non-penalty shots: average chance quality. |

## Defending & duels
| Metric | Definition |
|---|---|
| Tackles / interceptions / recoveries / clearances | Count of the matching event type. |
| Aerials won | `Aerial` events with outcome `Successful`. |
| Take-ons won | `TakeOn` events with outcome `Successful`. |
| Fouls committed | `Foul` events with outcome `Unsuccessful` (the fouling player's side of the pair). |

## Data checks that run on every build
- Each match's goals credited to players, plus own goals, equal the final score.
- Each team's player-minutes add up to 11 × match length, allowing for red cards (±5 min).
- Event, player-match and player-season rows are unique; minutes are between 0 and 140.
- Every team name maps to a short code and across both sources (`seeds/team_names.csv`).
