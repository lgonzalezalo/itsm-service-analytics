select *
from {{ ref('fct_sla') }}
where response_sla_rate   not between 0 and 1
   or resolution_sla_rate not between 0 and 1
   or reopen_rate         not between 0 and 1
