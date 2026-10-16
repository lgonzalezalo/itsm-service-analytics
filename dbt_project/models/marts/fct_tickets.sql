{{ config(
    materialized = 'incremental',
    unique_key = 'ticket_id',
    incremental_strategy = 'delete+insert'
) }}

-- One row per incident: timings in minutes and SLA outcome against sla_targets.
-- Incremental: each run only reads versions newer than the last run, plus every
-- ticket that is still open (its SLA outcome changes as time passes).

with changed as (
    -- Filter BEFORE the window function, otherwise the whole history is scanned.
    select * from {{ ref('stg_ticket_events') }}
    {% if is_incremental() %}
    where updated_at >= (select max(updated_at) from {{ this }})
       or ticket_id in (select ticket_id from {{ this }} where is_open)
    {% endif %}
),

latest as (
    select *
    from changed
    qualify row_number() over (
        partition by ticket_id
        order by
            updated_at desc,
            (responded_at is not null)::int + (resolved_at is not null)::int + is_reopened::int desc
    ) = 1
),

targets as (
    select
        priority,
        response_minutes       as target_response_minutes,
        resolution_hours * 60  as target_resolution_minutes
    from {{ ref('sla_targets') }}
),

-- Cut-off: how far the data reaches (latest change seen in any batch).
as_of as (
    select max(updated_at) as as_of from {{ ref('stg_ticket_events') }}
),

timed as (
    select
        t.*,
        g.target_response_minutes,
        g.target_resolution_minutes,
        date_diff('minute', t.opened_at, t.responded_at) as response_minutes,
        date_diff('minute', t.opened_at, t.resolved_at)  as resolution_minutes,
        date_diff('minute', t.opened_at, a.as_of)        as age_minutes
    from latest t
    join targets g using (priority)
    cross join as_of a
)

select
    ticket_id,
    client,
    team,
    category,
    subcategory,
    priority,
    opened_at,
    date_trunc('month', opened_at)  as opened_month,
    response_minutes,               -- null until the first response
    resolution_minutes,             -- null while the ticket is open
    effort_minutes,                 -- hands-on minutes; null while open
    resolved_at is null             as is_open,
    is_reopened,
    problem_id,
    problem_id is not null          as has_problem,
    response_minutes <= target_response_minutes as response_sla_met,
    case
        when resolved_at is not null then resolution_minutes <= target_resolution_minutes
        when age_minutes > target_resolution_minutes then false
        -- else null: open and still inside the target, outcome undetermined
    end                             as resolution_sla_met,
    updated_at
from timed
