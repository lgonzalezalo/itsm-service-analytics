-- One row per ticket VERSION (a ticket appears once per state change).
-- Reads every daily batch; this is the raw, append-only history.
select
    ticket_id,
    client,
    team,
    case
        when category is null or lower(category) = 'other' then 'uncategorised'
        else category
    end                                     as category,
    coalesce(subcategory, 'uncategorised')  as subcategory,
    priority,
    cast(opened_at as timestamp)            as opened_at,
    cast(responded_at as timestamp)         as responded_at,
    cast(resolved_at as timestamp)          as resolved_at,
    cast(effort_minutes as integer)         as effort_minutes,   -- hands-on time, set on resolve
    cast(reopened as integer) = 1           as is_reopened,
    problem_id,
    cast(updated_at as timestamp)           as updated_at
from read_csv('data/raw/tickets/tickets_*.csv', header = true, all_varchar = true)
