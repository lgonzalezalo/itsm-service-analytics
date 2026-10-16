"""Synthetic ITSM generator: incidents + problems. Fictional data, reproducible by seed."""
import argparse
import csv
import math
import os
import random
from datetime import datetime, timedelta

# subcategory -> (team, category, volume weight, severity profile, speed factor, median effort minutes)
# speed scales the elapsed resolution time; effort is hands-on time (ITSM "time worked").
SUBCATEGORIES = {
    "password_reset":     ("Workplace",  "access",      26, "low",  0.05,   6),
    "vpn_access":         ("Workplace",  "network",     12, "med",  0.30,  25),
    "laptop_issue":       ("Workplace",  "hardware",     9, "low",  1.00,  90),
    "software_install":   ("Workplace",  "software",     5, "low",  0.50,  20),
    "disk_space":         ("Databases",  "storage",     11, "high", 0.70,  45),
    "slow_query":         ("Databases",  "performance",  8, "med",  1.00, 120),
    "access_request":     ("Databases",  "access",       4, "low",  0.40,  15),
    "backup_failure":     ("Databases",  "backup",       3, "high", 0.80,  90),
    "queue_backlog":      ("Middleware", "messaging",    7, "high", 0.80,  60),
    "deploy_failure":     ("Middleware", "deployment",   5, "high", 1.00, 150),
    "certificate_expiry": ("Middleware", "security",     3, "high", 0.60,  30),
    "batch_abend":        ("Mainframe",  "batch",        5, "high", 0.70,  75),
    "storage_alert":      ("Mainframe",  "storage",      2, "med",  0.80,  40),
    "job_scheduling":     ("Mainframe",  "batch",        2, "med",  0.70,  35),
}
TEAM_SLOWNESS = {"Workplace": 0.8, "Databases": 1.0, "Middleware": 1.1, "Mainframe": 1.3}
# severity profile -> priority weights (critical subcategories raise more P1/P2)
SEVERITY = {
    "low":  {"P1": 0, "P2": 3,  "P3": 27, "P4": 70},
    "med":  {"P1": 1, "P2": 9,  "P3": 40, "P4": 50},
    "high": {"P1": 4, "P2": 20, "P3": 46, "P4": 30},
}
# priority -> (median response minutes, median resolution hours); kept well under the SLA targets
PRIORITIES = {"P1": (7, 2), "P2": (25, 4), "P3": (100, 12), "P4": (240, 36)}
CLIENTS = ["Client-A", "Client-B", "Client-C", "Client-D"]
ROOT_CAUSES = ["capacity", "configuration", "software_defect", "process_gap", "third_party"]
TICKET_FIELDS = ["ticket_id", "client", "team", "category", "subcategory", "priority",
                 "opened_at", "responded_at", "resolved_at", "effort_minutes", "reopened", "problem_id"]
PROBLEM_FIELDS = ["problem_id", "subcategory", "opened_at", "closed_at", "root_cause", "pir_completed"]
BATCH_FIELDS = TICKET_FIELDS + ["updated_at"]


def lognormal(rng, median, sigma):
    return rng.lognormvariate(math.log(median), sigma)


def fmt(dt):
    return dt.isoformat(sep=" ", timespec="minutes")


def opened_at(rng, start, days):
    while True:
        day = start + timedelta(days=rng.randrange(days))
        if day.weekday() < 5 or rng.random() < 0.15:  # weekends: only 15% kept
            hour = round(rng.triangular(0, 23, 11))     # (low, high, mode): peak at 11h
            return day.replace(hour=hour, minute=rng.randrange(60))


def make_ticket(rng, start, days, end):
    names = list(SUBCATEGORIES)
    sub = rng.choices(names, [SUBCATEGORIES[n][2] for n in names])[0]
    team, cat, _, severity, speed, effort_median = SUBCATEGORIES[sub]
    weights = SEVERITY[severity]
    prio = rng.choices(list(weights), list(weights.values()))[0]
    resp_min, res_h = PRIORITIES[prio]
    slow = TEAM_SLOWNESS[team]
    opened = opened_at(rng, start, days)
    responded = opened + timedelta(minutes=lognormal(rng, resp_min * slow, 0.7))
    resolved = responded + timedelta(hours=lognormal(rng, res_h * slow * speed, 0.6))
    elapsed = (resolved - opened).total_seconds() / 60
    effort = min(lognormal(rng, effort_median, 0.5), 0.8 * elapsed)  # never above 80% of elapsed
    shown_cat, shown_sub = (cat, sub)
    if rng.random() < 0.08:  # agents sometimes leave it blank or pick "Other"
        shown_cat, shown_sub = rng.choice(["", "Other"]), ""
    return {
        "ticket_id": "", "client": rng.choice(CLIENTS), "team": team,
        "category": shown_cat, "subcategory": shown_sub, "priority": prio,
        "opened_at": fmt(opened), "responded_at": fmt(responded),
        "resolved_at": "" if resolved > end else fmt(resolved),
        "effort_minutes": "" if resolved > end else max(1, round(effort)),
        "reopened": int(rng.random() < (0.12 if team == "Mainframe" else 0.05)),
        "problem_id": "", "_true_sub": sub,
    }


def link_problems(rng, rows, end):
    """A P1/P2 can open a problem; later tickets of the same subcategory may link to it."""
    problems, active = [], {}
    for r in rows:
        sub, opened = r["_true_sub"], datetime.fromisoformat(r["opened_at"])
        p = active.get(sub)
        if p and opened > p["_closes"]:
            p = None
        opens = p is None and r["priority"] in ("P1", "P2") and rng.random() < 0.5
        if opens:
            closes = opened + timedelta(days=lognormal(rng, 20, 0.5))
            p = {"problem_id": f"PRB{len(problems) + 1:05d}", "subcategory": sub,
                 "opened_at": r["opened_at"], "root_cause": rng.choice(ROOT_CAUSES),
                 "closed_at": "" if closes > end else fmt(closes),
                 "pir_completed": int(closes <= end and rng.random() < 0.7), "_closes": closes}
            problems.append(p)
        active[sub] = p
        link_chance = {"P1": 1.0, "P2": 0.6, "P3": 0.1, "P4": 0.03}[r["priority"]]
        if p and (opens or rng.random() < link_chance):
            r["problem_id"] = p["problem_id"]
    return problems


def parse(ts):
    return datetime.fromisoformat(ts) if ts else None


def build_events(rows, end, seed):
    """Turn each ticket's final state into the versions an ITSM extract by updated_at
    would return: opened -> responded -> resolved -> reopened. Also makes the final rows
    consistent with what could have happened before the cut-off date."""
    rng = random.Random(seed + 1)  # separate stream: the main data keeps its randomness
    events = []
    for r in rows:
        opened = parse(r["opened_at"])
        responded, resolved = parse(r["responded_at"]), parse(r["resolved_at"])
        if responded and responded > end:      # not answered yet at cut-off
            r["responded_at"], responded = "", None
        reopen_at = None
        if r["reopened"]:
            if resolved:
                reopen_at = resolved + timedelta(hours=rng.uniform(1, 48))
            if reopen_at is None or reopen_at > end:
                r["reopened"], reopen_at = 0, None
        states = [(opened, {})]
        if responded:
            states.append((responded, {"responded_at": r["responded_at"], "problem_id": r["problem_id"]}))
        if resolved:
            states.append((resolved, {"resolved_at": r["resolved_at"], "effort_minutes": r["effort_minutes"]}))
        if reopen_at:
            states.append((reopen_at, {"reopened": 1}))
        current = dict(r, responded_at="", resolved_at="", effort_minutes="", reopened=0, problem_id="")
        for ts, change in states:
            current.update(change)
            current["updated_at"] = fmt(ts)
            events.append(dict(current))
    return events


def write_batches(events, batch_dir):
    os.makedirs(batch_dir, exist_ok=True)
    for name in os.listdir(batch_dir):
        if name.startswith("tickets_") and name.endswith(".csv"):
            os.remove(os.path.join(batch_dir, name))
    by_day = {}
    for e in events:
        by_day.setdefault(e["updated_at"][:10], []).append(e)
    for day, evs in sorted(by_day.items()):
        evs.sort(key=lambda e: (e["updated_at"], e["ticket_id"]))
        write_csv(os.path.join(batch_dir, f"tickets_{day}.csv"), BATCH_FIELDS, evs)
    return len(by_day)


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickets", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--batch-dir", default="data/raw/tickets")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    start = datetime.fromisoformat(a.start)
    end = start + timedelta(days=a.days)
    rows = [make_ticket(rng, start, a.days, end) for _ in range(a.tickets)]
    rows.sort(key=lambda r: r["opened_at"])
    for i, r in enumerate(rows, 1):
        r["ticket_id"] = f"INC{i:06d}"
    problems = link_problems(rng, rows, end)
    events = build_events(rows, end, a.seed)   # may adjust rows: do it before writing
    os.makedirs(a.out_dir, exist_ok=True)
    write_csv(os.path.join(a.out_dir, "tickets.csv"), TICKET_FIELDS, rows)
    write_csv(os.path.join(a.out_dir, "problems.csv"), PROBLEM_FIELDS, problems)
    n_days = write_batches(events, a.batch_dir)
    print(f"{len(rows)} tickets, {len(problems)} problems -> {a.out_dir}/ (seed={a.seed})")
    print(f"{len(events)} versions in {n_days} daily batches -> {a.batch_dir}/")


if __name__ == "__main__":
    main()
