# ITSM Service Analytics

A small, end-to-end analytics project on IT service management data: **SLA/SLO tracking, MTTR, problem management and automation candidates**, built with Python, dbt and DuckDB, with a static dashboard.

**Live dashboard:** https://lgonzalezalo.github.io/itsm-service-analytics/

> **All data is synthetic.** Nothing here comes from a real client or a real ITSM tool.

<!-- Add 2-3 screenshots here: docs/img/*.png -->

## Questions it answers

- Are we meeting response and resolution SLAs, by team and priority, month by month?
- Where does the load sit, in tickets and in effort?
- Which recurring ticket types would be worth automating first, and what do reopen rate, problem links and SLA breaches say about that ranking?

## Architecture

```
generator/generate_tickets.py   synthetic tickets, one CSV batch per day (+ problems.csv)
        │
dbt (dbt-duckdb)                staging views → incremental fct_tickets → fct_sla, automation_candidates
        │
data/itsm.duckdb                local database (not committed)
        │
scripts/export_dashboard_data.py   final tables → docs/data/*.json
        │
docs/index.html                 static page (Observable Plot), served by GitHub Pages
```

- **Incremental load:** `fct_tickets` uses `delete+insert` on `ticket_id`. New daily batches only reprocess changed tickets and tickets still open (their SLA outcome depends on time).
- **Proof, not claim:** a test (`assert_incremental_matches_full_recompute`) checks the incremental table against a full recompute.
- **Tests:** 18 dbt data tests (generic and singular) cover keys, accepted values, relationships, date ordering, SLA rate ranges, grain and Pareto consistency.

## Reproduce it

Requires Python 3.12 (tested on macOS). From the repo root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python generator/generate_tickets.py          # 5,000 tickets, seed 42, 180 days
dbt build --project-dir dbt_project --profiles-dir dbt_project
python scripts/export_dashboard_data.py       # writes docs/data/*.json
python -m http.server 8000 -d docs            # open http://localhost:8000
```

To see the incremental load work (withholds 30 days of batches, builds, adds them back, builds again):

```bash
python scripts/incremental_demo.py
```

## Assumptions and limitations

- **Synthetic data.** Rankings and rates reflect the generator's parameters, not real operations.
- **SLA targets are my own assumptions** (`dbt_project/seeds/sla_targets.csv`): P1 15 min / 4 h, P2 60 min / 8 h, P3 240 min / 24 h, P4 480 min / 72 h.
- **Effort is an invented field** (minutes actually worked). It is not elapsed time, and real tools often don't capture it reliably.
- **Field names are modelled on typical ITSM exports** and have not been checked against a specific product.
- **The automation ranking uses total effort only.** It does not score how automatable each case is; reopen rate, problem links and breaches are shown next to it, not inside it.
- **Dashboard aggregates:** rates are combined weighted by ticket count; P90 can't be combined, so the table shows the worst monthly value. Groups with fewer than 30 tickets are flagged.
- **Scale:** at 5,000 rows the incremental model gives no measurable speed-up. It demonstrates the pattern, not a benchmark. In production, the `as_of` calculation would come from a watermark table instead of scanning history.

## Stack

Python (stdlib generator) · dbt Core + dbt-duckdb · DuckDB · Observable Plot / D3 (loaded from a CDN)
