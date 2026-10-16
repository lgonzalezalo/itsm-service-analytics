"""Proves the incremental fct_tickets: build on 150 days, then add 30 and rebuild.

Run from the repo root with the venv active:  python scripts/incremental_demo.py
`dbt build` exits non-zero if any test fails, including the reconciliation test
(incremental result == full recomputation), so reaching the summary means they passed.
"""
import pathlib
import shutil
import subprocess

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
TICKETS = ROOT / "data/raw/tickets"
LATER = ROOT / "data/raw/later"
DB = ROOT / "data/itsm.duckdb"
HELD_BACK = 30  # most recent daily batches to withhold


def build(*extra):
    cmd = ["dbt", "build", "--project-dir", "dbt_project", "--profiles-dir", "dbt_project", *extra]
    subprocess.run(cmd, cwd=ROOT, check=True)


def query(sql, *params):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql, list(params)).fetchone()
    finally:
        con.close()


def move(files, dest):
    for f in files:
        shutil.move(str(f), str(dest / f.name))


def main():
    LATER.mkdir(exist_ok=True)
    held = sorted(TICKETS.glob("tickets_*.csv"))[-HELD_BACK:]
    try:
        print(f"\n== 1. Withholding the last {len(held)} daily batches")
        move(held, LATER)
        print("\n== 2. Full build on the remaining days")
        build("--full-refresh")
        n0, t0 = query("select count(*), max(updated_at) from fct_tickets")
        print(f"\n== 3. The {len(held)} new days arrive")
        move([LATER / f.name for f in held], TICKETS)
        print("\n== 4. Incremental build (no --full-refresh)")
        build()
        n1, t1 = query("select count(*), max(updated_at) from fct_tickets")
        (touched,) = query("select count(*) from fct_tickets where updated_at >= ?", t0)
    finally:  # never leave batches parked, even if a build fails
        move(sorted(LATER.glob("tickets_*.csv")), TICKETS)

    print("\n================ SUMMARY ================")
    print(f"Before: {n0} tickets, data up to {t0}")
    print(f"After : {n1} tickets, data up to {t1}")
    print(f"Tickets with a version newer than the first load: {touched}")
    print("All tests passed, including incremental == full recompute.")


if __name__ == "__main__":
    main()
