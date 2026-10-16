-- Resolved tickets must carry effort, and effort cannot exceed elapsed time.
select ticket_id
from {{ ref('stg_tickets') }}
where (resolved_at is not null and effort_minutes is null)
   or (resolved_at is null     and effort_minutes is not null)
   or effort_minutes > date_diff('minute', opened_at, resolved_at)
