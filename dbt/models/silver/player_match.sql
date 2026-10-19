-- One row per player per match they actually played in, with minutes on the pitch.
--
-- Minutes use WhoScored's "expanded" minute, which counts stoppage time, so a full
-- match is often 95-100 minutes rather than 90. Players sent off stop at the card.

with lineups as (
    select * from {{ source('bronze', 'whoscored_players') }}
),

matches as (
    select match_id, max_minute_expanded from {{ ref('stg_matches') }}
),

sent_off as (
    select match_id, player_id, min(expanded_minute) as sent_off_minute
    from {{ ref('stg_events') }}
    where card_type in ('Red', 'SecondYellow')
    group by all
),

spans as (
    select
        l.match_id,
        l.team_id,
        l.player_id,
        l.player,
        l.position,
        l.is_starter,
        case when l.is_starter then 0 else l.subbed_in_minute end as on_minute,
        least(
            coalesce(l.subbed_out_minute, m.max_minute_expanded),
            coalesce(s.sent_off_minute, m.max_minute_expanded)
        ) as off_minute,
        s.sent_off_minute is not null as was_sent_off
    from lineups l
    join matches m using (match_id)
    left join sent_off s using (match_id, player_id)
)

select
    *,
    off_minute - on_minute as minutes
from spans
where is_starter or on_minute is not null  -- drop unused substitutes
