-- The incremental fct_tickets must equal a full recomputation from the event history.
select coalesce(f.ticket_id, s.ticket_id) as ticket_id
from {{ ref('fct_tickets') }} f
full outer join {{ ref('stg_tickets') }} s on f.ticket_id = s.ticket_id
where f.ticket_id is null
   or s.ticket_id is null
   or f.updated_at   is distinct from s.updated_at
   or f.is_open      is distinct from (s.resolved_at is null)
   or f.is_reopened  is distinct from s.is_reopened
   or f.effort_minutes is distinct from s.effort_minutes
   or f.problem_id   is distinct from s.problem_id
