-- Current state of each ticket = its latest version.
-- Full recomputation over all history: used for tests and as the reference
-- that the incremental fct_tickets must reproduce.
select *
from {{ ref('stg_ticket_events') }}
qualify row_number() over (
    partition by ticket_id
    order by
        updated_at desc,
        -- tie-break if two versions share the same minute: keep the most complete
        (responded_at is not null)::int + (resolved_at is not null)::int + is_reopened::int desc
) = 1
