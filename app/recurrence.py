"""Recurring calendar rules with per-day exceptions; no duplicated future rows."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException
from .main import connect


def init_recurrence_db() -> None:
    """Back up before upgrading. Migration is atomic and preserves v1-v3 data."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (3, 4, 5):
            raise RuntimeError(f"Expected v3 or v4 database, got {version}")
        db.execute("""
            CREATE TABLE IF NOT EXISTS recurring_rules (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_name TEXT NOT NULL,
              start_day TEXT NOT NULL,
              until_day TEXT,
              weekdays TEXT NOT NULL,
              scheduled_time TEXT NOT NULL,
              end_time TEXT NOT NULL,
              expected_delta INTEGER CHECK(expected_delta BETWEEN -100 AND 100),
              created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS recurring_exceptions (
              rule_id INTEGER NOT NULL REFERENCES recurring_rules(id) ON DELETE CASCADE,
              occurrence_day TEXT NOT NULL,
              action TEXT NOT NULL CHECK(action IN ('modified','skipped','completed')),
              activity_name TEXT,
              scheduled_time TEXT,
              end_time TEXT,
              expected_delta INTEGER CHECK(expected_delta BETWEEN -100 AND 100),
              linked_entry_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
              PRIMARY KEY (rule_id, occurrence_day)
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_recurring_dates ON recurring_rules(start_day,until_day)")
        if version == 3:
            db.execute("PRAGMA user_version=4")


def parse_repeat(pattern: str, start_day: date, custom_days: list[str]) -> str:
    """Seven weekdays encoded as numeric indices; empty/custom invalid."""
    if pattern == "daily":
        weekdays = set(range(7))
    elif pattern == "weekdays":
        weekdays = set(range(5))
    elif pattern == "weekly":
        weekdays = {start_day.weekday()}
    elif pattern == "custom":
        if not custom_days or any(day not in {str(i) for i in range(7)} for day in custom_days):
            raise HTTPException(422, "Select valid weekdays.")
        weekdays = {int(day) for day in custom_days}
    else:
        raise HTTPException(422, "Invalid recurrence frequency.")
    return ",".join(str(day) for day in sorted(weekdays))


def read_rule(db, rule_id: int):
    rule = db.execute("SELECT * FROM recurring_rules WHERE id=?", (rule_id,)).fetchone()
    if not rule:
        raise HTTPException(404, "Recurring series not found.")
    return rule


def applies(rule, day: date) -> bool:
    if day < date.fromisoformat(rule["start_day"]):
        return False
    if rule["until_day"] and day > date.fromisoformat(rule["until_day"]):
        return False
    return str(day.weekday()) in rule["weekdays"].split(",")


def assert_occurrence(rule, day: date) -> None:
    if not applies(rule, day):
        raise HTTPException(404, "Not an occurrence of this recurring series.")


def recurring_plans(start: date, end: date) -> list[dict]:
    """Expand only the requested [start,end) range; no infinite generation."""
    with connect() as db:
        rules = db.execute(
            "SELECT * FROM recurring_rules WHERE start_day < ? "
            "AND (until_day IS NULL OR until_day >= ?) ORDER BY id",
            (end.isoformat(), start.isoformat()),
        ).fetchall()
        exceptions = db.execute(
            "SELECT * FROM recurring_exceptions WHERE occurrence_day>=? AND occurrence_day<?",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    by_key = {(row["rule_id"], row["occurrence_day"]): row for row in exceptions}
    result = []
    current = start
    while current < end:
        for rule in rules:
            if not applies(rule, current):
                continue
            exception = by_key.get((rule["id"], current.isoformat()))
            if exception and exception["action"] in ("skipped", "completed"):
                continue
            overrides = exception and exception["action"] == "modified"
            result.append({
                "id": rule["id"], "rule_id": rule["id"], "recurring": True,
                "scheduled_day": current.isoformat(),
                "activity_name": exception["activity_name"] if overrides else rule["activity_name"],
                "scheduled_time": exception["scheduled_time"] if overrides else rule["scheduled_time"],
                "end_time": exception["end_time"] if overrides else rule["end_time"],
                "expected_delta": exception["expected_delta"] if overrides else rule["expected_delta"],
                "status": "planned", "linked_entry_id": None,
            })
        current += timedelta(days=1)
    return result


def occurrence_plan(rule_id: int, day: date) -> dict:
    """Resolve an editable occurrence through the same expansion as the calendar."""
    plans = recurring_plans(day, day + timedelta(days=1))
    for plan in plans:
        if plan["rule_id"] == rule_id:
            return plan
    raise HTTPException(404, "Recurring activity not found for this day.")


def write_exception(db, rule_id: int, day: date, action: str,
                    name: str | None = None, start: str | None = None,
                    end: str | None = None, delta: int | None = None,
                    entry_id: int | None = None) -> None:
    db.execute(
        "INSERT INTO recurring_exceptions "
        "(rule_id,occurrence_day,action,activity_name,scheduled_time,end_time,expected_delta,linked_entry_id) "
        "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(rule_id,occurrence_day) DO UPDATE SET "
        "action=excluded.action,activity_name=excluded.activity_name,"
        "scheduled_time=excluded.scheduled_time,end_time=excluded.end_time,"
        "expected_delta=excluded.expected_delta,linked_entry_id=excluded.linked_entry_id",
        (rule_id, day.isoformat(), action, name, start, end, delta, entry_id),
    )
