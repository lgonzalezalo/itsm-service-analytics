-- SLA and service health by month, team and priority.
select
    opened_month,
    team,
    priority,
    count(*)                                                 as tickets,
    count(*) filter (where is_open)                          as open_tickets,
    round(avg(response_sla_met::int), 3)                     as response_sla_rate,
    round(avg(resolution_sla_met::int), 3)                   as resolution_sla_rate,
    round(avg(resolution_minutes) / 60.0, 1)                 as mttr_hours,
    round(quantile_cont(resolution_minutes, 0.9) / 60.0, 1)  as p90_resolution_hours,
    round(avg(is_reopened::int), 3)                          as reopen_rate
from {{ ref('fct_tickets') }}
group by all
