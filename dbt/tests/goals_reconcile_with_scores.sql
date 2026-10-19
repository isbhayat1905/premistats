-- Every match: goals credited to players + own goals must equal the final score.
-- If this fails, we're mis-counting goals somewhere (or the source is inconsistent).
with scored as (
    select match_id, count(*) as event_goals
    from {{ ref('stg_events') }}
    where is_goal
    group by match_id
)

select m.match_id, m.home_goals + m.away_goals as score_goals, coalesce(s.event_goals, 0) as event_goals
from {{ ref('stg_matches') }} m
left join scored s using (match_id)
where m.home_goals + m.away_goals <> coalesce(s.event_goals, 0)
