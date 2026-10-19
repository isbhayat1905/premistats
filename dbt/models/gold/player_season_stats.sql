-- One row per player per season: volume stats plus per-90 rates.
-- This is the table behind the player pages and the X/Y chart builder.

{% set counts = [
    'touches', 'touches_in_box', 'passes', 'passes_completed', 'open_play_passes',
    'progressive_passes', 'passes_into_box', 'crosses', 'long_balls', 'through_balls',
    'chances_created', 'big_chances_created', 'assists',
    'shots', 'shots_on_target', 'goals', 'non_penalty_goals', 'headed_shots',
    'take_ons', 'take_ons_won', 'tackles', 'interceptions', 'ball_recoveries',
    'clearances', 'aerials', 'aerials_won', 'fouls_committed', 'dispossessed',
] %}

with appearances as (
    select
        m.season,
        pm.player_id,
        any_value(pm.player) as player,
        -- the team the player spent most minutes with (handles mid-season transfers)
        arg_max(t.team, pm.minutes) as team,
        mode(pm.position) filter (where pm.position <> 'Sub') as position,
        count(*) as appearances,
        count(*) filter (where pm.is_starter) as starts,
        sum(pm.minutes) as minutes
    from {{ ref('player_match') }} pm
    join {{ ref('stg_matches') }} m using (match_id)
    join (
        select match_id, home_team_id as team_id, home_team as team from {{ ref('stg_matches') }}
        union all
        select match_id, away_team_id, away_team from {{ ref('stg_matches') }}
    ) t using (match_id, team_id)
    group by all
),

actions as (
    select
        m.season,
        e.player_id,
        count(*) filter (where e.is_touch) as touches,
        count(*) filter (where e.is_touch and e.starts_in_box) as touches_in_box,
        count(*) filter (where e.is_pass) as passes,
        count(*) filter (where e.is_completed_pass) as passes_completed,
        count(*) filter (where e.is_open_play_pass) as open_play_passes,
        count(*) filter (where e.is_progressive_pass) as progressive_passes,
        count(*) filter (where e.is_pass_into_box) as passes_into_box,
        count(*) filter (where e.is_pass and e.is_cross) as crosses,
        count(*) filter (where e.is_pass and e.is_long_ball) as long_balls,
        count(*) filter (where e.is_pass and e.is_through_ball) as through_balls,
        count(*) filter (where e.is_chance_created) as chances_created,
        count(*) filter (where e.is_big_chance_created) as big_chances_created,
        count(*) filter (where e.is_assist) as assists,
        count(*) filter (where e.is_shot_attempt) as shots,
        count(*) filter (where e.is_shot_on_target) as shots_on_target,
        count(*) filter (where e.is_goal and not e.is_own_goal) as goals,
        count(*) filter (where e.is_goal and not e.is_own_goal and not e.is_penalty) as non_penalty_goals,
        count(*) filter (where e.is_shot_attempt and e.is_header) as headed_shots,
        count(*) filter (where e.type = 'TakeOn') as take_ons,
        count(*) filter (where e.type = 'TakeOn' and e.outcome = 'Successful') as take_ons_won,
        count(*) filter (where e.type = 'Tackle') as tackles,
        count(*) filter (where e.type = 'Interception') as interceptions,
        count(*) filter (where e.type = 'BallRecovery') as ball_recoveries,
        count(*) filter (where e.type = 'Clearance') as clearances,
        count(*) filter (where e.type = 'Aerial') as aerials,
        count(*) filter (where e.type = 'Aerial' and e.outcome = 'Successful') as aerials_won,
        count(*) filter (where e.type = 'Foul' and e.outcome = 'Unsuccessful') as fouls_committed,
        count(*) filter (where e.type = 'Dispossessed') as dispossessed
    from {{ ref('stg_events') }} e
    join {{ ref('stg_matches') }} m using (match_id)
    where e.player_id is not null
    group by all
)

select
    a.season,
    a.player_id,
    a.player,
    a.team,
    a.position,
    a.appearances,
    a.starts,
    a.minutes,
    {% for c in counts %}
    coalesce(x.{{ c }}, 0) as {{ c }},
    {% endfor %}
    round(x.passes_completed / nullif(x.passes, 0), 3) as pass_completion,
    round(x.take_ons_won / nullif(x.take_ons, 0), 3) as take_on_success,
    round(x.aerials_won / nullif(x.aerials, 0), 3) as aerial_win_rate,
    {% for c in counts %}
    round(coalesce(x.{{ c }}, 0) * 90.0 / nullif(a.minutes, 0), 2) as {{ c }}_p90{{ "," if not loop.last }}
    {% endfor %}
from appearances a
left join actions x using (season, player_id)
