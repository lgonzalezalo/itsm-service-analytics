"""Exporta las tablas finales de dbt a JSON para el panel estático."""
import json
import duckdb

DB = "data/itsm.duckdb"
OUT = "docs/data"

QUERIES = {
    "sla": "select * from fct_sla order by opened_month, team, priority",
    "team_load": """
        select opened_month, team,
               count(*) as tickets,
               round(sum(effort_minutes) / 60.0, 1) as effort_hours
        from fct_tickets group by all order by 1, 2""",
    "automation": "select * from automation_candidates order by automation_rank",
}

con = duckdb.connect(DB, read_only=True)
for name, sql in QUERIES.items():
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    with open(f"{OUT}/{name}.json", "w") as f:
        json.dump(rows, f, default=str)
    print(f"{name}: {len(rows)} filas -> {OUT}/{name}.json")
