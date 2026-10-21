-- One row per WhoScored shot (own goals excluded), described in the same vocabulary as
-- the StatsBomb training data, so the xG model sees identical features from both sources.
-- Shared vocabulary: xg/features.py. Mapping table: docs/metrics.md#xg.

with shots as (
    select * from {{ ref('stg_events') }}
    where is_shot_attempt
),

assist as (
    -- A shot's related_event_id is the team-level sequence number of the action that set it up.
    select match_id, team_id, team_event_seq, q as assist_q, type as assist_type
    from {{ ref('stg_events') }}
)

select
    s.match_id,
    s.event_index,
    s.team_id,
    s.player_id,
    case when a.assist_type = 'Pass' then s.related_player_id end as assist_player_id,
    s.period,
    s.minute,
    s.expanded_minute,
    s.x,
    s.y,
    case
        when list_contains(s.q, 'Head') then 'head'
        when list_contains(s.q, 'OtherBodyPart') then 'other'
        else 'foot'
    end as body_part,
    case
        when list_contains(s.q, 'Penalty') then 'penalty'
        when list_contains(s.q, 'DirectFreekick') then 'free_kick_direct'
        when list_contains(s.q, 'FromCorner') then 'corner'
        when list_has_any(s.q, ['SetPiece', 'ThrowinSetPiece']) then 'set_piece_other'
        when list_contains(s.q, 'FastBreak') then 'counter'
        else 'open_play'
    end as situation,
    list_contains(s.q, 'FirstTouch') as first_time,
    list_contains(s.q, 'OneOnOne') as one_on_one,
    list_contains(s.q, 'Volley') as volley,
    a.team_event_seq is not null as assisted,
    coalesce(a.assist_type = 'Pass' and list_contains(a.assist_q, 'Cross'), false) as assist_cross,
    coalesce(a.assist_type = 'Pass' and list_contains(a.assist_q, 'Throughball'), false) as assist_through_ball,
    s.is_big_chance,
    s.is_shot_on_target,
    s.is_goal
from shots s
left join assist a
    on a.match_id = s.match_id
    and a.team_id = s.team_id
    and a.team_event_seq = s.related_event_id
