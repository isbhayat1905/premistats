-- One row per WhoScored event, enriched with the flags every downstream stat needs.
--
-- Coordinates stay on the 0-100 scale (decision 006), each team attacking towards x = 100.
-- Distances are converted to metres using a standard 105 x 68 m pitch.

with events as (
    select
        *,
        list_transform(
            from_json(qualifiers, '[{"type": {"displayName": "VARCHAR"}, "value": "VARCHAR"}]'),
            q -> q.type.displayName
        ) as q
    from {{ source('bronze', 'whoscored_events') }}
),

flagged as (
    select
        *,
        type = 'Pass' as is_pass,
        type = 'Pass' and outcome = 'Successful' as is_completed_pass,
        type = 'Pass' and not list_has_any(q, ['CornerTaken', 'FreekickTaken', 'ThrowIn', 'GoalKick', 'KeeperThrow'])
            as is_open_play_pass,
        list_contains(q, 'Cross') as is_cross,
        list_contains(q, 'Longball') as is_long_ball,
        list_contains(q, 'Throughball') as is_through_ball,
        list_contains(q, 'KeyPass') or list_contains(q, 'IntentionalGoalAssist') as is_chance_created,
        list_contains(q, 'IntentionalGoalAssist') as is_assist,
        list_contains(q, 'BigChanceCreated') as is_big_chance_created,

        is_shot and not is_own_goal as is_shot_attempt,
        is_shot and (type = 'Goal' or (type = 'SavedShot' and not list_contains(q, 'Blocked'))) and not is_own_goal
            as is_shot_on_target,
        list_contains(q, 'Penalty') as is_penalty,
        list_contains(q, 'Head') as is_header,
        list_contains(q, 'BigChance') as is_big_chance,

        -- Penalty area on the 0-100 scale: x >= 83, 21.1 <= y <= 78.9
        x >= 83 and y between 21.1 and 78.9 as starts_in_box,
        end_x >= 83 and end_y between 21.1 and 78.9 as ends_in_box,
        x >= 66.7 as starts_in_final_third,

        sqrt(power((100 - x) * 1.05, 2) + power((50 - y) * 0.68, 2)) as dist_to_goal_m,
        sqrt(power((100 - end_x) * 1.05, 2) + power((50 - end_y) * 0.68, 2)) as end_dist_to_goal_m
    from events
)

select
    *,
    -- Progressive pass: a completed open-play pass that moves the ball at least 25% closer
    -- to the centre of the opponent's goal, starting outside the defensive 40% of the pitch.
    -- (A common public definition, documented in docs/metrics.md.)
    is_completed_pass and is_open_play_pass and x >= 40
        and end_dist_to_goal_m <= 0.75 * dist_to_goal_m as is_progressive_pass,
    is_completed_pass and not starts_in_box and ends_in_box and not list_contains(q, 'CornerTaken')
        as is_pass_into_box
from flagged
