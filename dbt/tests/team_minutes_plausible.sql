-- A team's player-minutes should be ~11 x match length, minus time lost to red cards.
-- Flags any team-match more than 5 minutes off after allowing for sendings-off.
with team_minutes as (
    select
        pm.match_id,
        pm.team_id,
        sum(pm.minutes) as minutes,
        sum(case when pm.was_sent_off then m.max_minute_expanded - pm.off_minute else 0 end) as minutes_lost_to_reds,
        max(m.max_minute_expanded) * 11 as expected
    from {{ ref('player_match') }} pm
    join {{ ref('stg_matches') }} m using (match_id)
    group by all
)

select *
from team_minutes
where abs(minutes + minutes_lost_to_reds - expected) > 5
