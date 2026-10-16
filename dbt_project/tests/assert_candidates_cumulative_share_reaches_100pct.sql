-- Returns a row (= fails) if the Pareto curve does not end at 100%.
select max(cumulative_share) as final_share
from {{ ref('automation_candidates') }}
having max(cumulative_share) not between 0.99 and 1.01
