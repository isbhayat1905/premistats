-- shot_xg must score every shot in stg_shots: no shot silently dropped.
select (select count(*) from {{ ref('stg_shots') }}) as shots,
       (select count(*) from {{ ref('shot_xg') }}) as scored
where (select count(*) from {{ ref('stg_shots') }}) <> (select count(*) from {{ ref('shot_xg') }})
