-- Understat shots with xG, keyed to WhoScored team names so the two sources can be joined.
select
    s.shot_id,
    s.match_id as understat_match_id,
    s.season,
    cast(s.kickoff_utc as date) as match_date,
    t.whoscored_name as team,
    s.player,
    s.minute,
    s.x,
    s.y,
    s.xg,
    s.body_part,
    s.situation,
    s.result,
    s.result = 'Goal' as is_goal
from {{ source('bronze', 'understat_shots') }} s
left join {{ ref('team_names') }} t on t.understat_name = s.team
