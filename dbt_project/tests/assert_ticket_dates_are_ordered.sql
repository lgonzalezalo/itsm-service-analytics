-- Returns offending rows; the test passes when it returns none.
select ticket_id
from {{ ref('stg_tickets') }}
where responded_at < opened_at
   or resolved_at  < responded_at
