-- One row per match, with each team's short code from the team_names seed.
select
    m.match_id,
    m.season,
    m.kickoff_local,
    cast(m.kickoff_local as date) as match_date,
    m.home_team_id,
    m.home_team,
    home.short_name as home_short,
    m.away_team_id,
    m.away_team,
    away.short_name as away_short,
    m.home_goals,
    m.away_goals,
    m.venue,
    m.attendance,
    m.referee,
    m.max_minute_expanded
from {{ source('bronze', 'whoscored_matches') }} m
left join {{ ref('team_names') }} home on home.whoscored_name = m.home_team
left join {{ ref('team_names') }} away on away.whoscored_name = m.away_team
