-- Ranks subcategories by hands-on effort spent, resolved tickets only.
-- Score = total effort hours (effort_minutes = time actually worked, not elapsed time).
-- volume_rank and mean_resolution_hours are shown to contrast effort with volume and waiting.
-- reopen_rate, problem_link_rate and resolution_breach_rate are informational:
-- they do NOT enter the score yet.
with base as (
    select *
    from {{ ref('fct_tickets') }}
    where not is_open
      and subcategory <> 'uncategorised'   -- unclassified work cannot be targeted
),

agg as (
    select
        team,
        category,
        subcategory,
        count(*)                                   as tickets,
        sum(effort_minutes)                        as total_effort_minutes,
        round(avg(effort_minutes), 1)              as mean_effort_minutes,
        round(avg(resolution_minutes) / 60.0, 1)   as mean_resolution_hours,
        round(avg(is_reopened::int), 3)            as reopen_rate,
        round(avg(has_problem::int), 3)            as problem_link_rate,
        round(1 - avg(resolution_sla_met::int), 3) as resolution_breach_rate
    from base
    group by all
)

select
    row_number() over (order by total_effort_minutes desc) as automation_rank,
    row_number() over (order by tickets desc)              as volume_rank,
    team,
    category,
    subcategory,
    tickets,
    mean_effort_minutes,
    round(total_effort_minutes / 60.0, 0)                  as total_effort_hours,
    round(total_effort_minutes / sum(total_effort_minutes) over (), 3) as share_of_total_effort,
    round(
        sum(total_effort_minutes) over (order by total_effort_minutes desc)
        / sum(total_effort_minutes) over (), 3
    )                                                      as cumulative_share,
    mean_resolution_hours,
    reopen_rate,
    problem_link_rate,
    resolution_breach_rate
from agg
order by automation_rank
