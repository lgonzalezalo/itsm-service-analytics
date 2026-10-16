select opened_month, team, priority, count(*) as n
from {{ ref('fct_sla') }}
group by all
having count(*) > 1
