-- One row per problem record (root-cause investigation).
select
    problem_id,
    subcategory,
    cast(opened_at as timestamp) as opened_at,
    cast(closed_at as timestamp) as closed_at,               -- null = still open
    root_cause,
    pir_completed = 1            as is_pir_completed
from read_csv_auto('data/problems.csv', header = true)
