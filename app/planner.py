"""Optional weekly planner, daily starting energy, and simple diary insights."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from statistics import median

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .main import (
    TZ, activity_rows, check_csrf, connect, date_bounds, local_time, parse_entry,
    parsed_day, require_login, templates, csrf,
)

router = APIRouter(prefix="/planner")


def initialize_planner_database() -> None:
    """Transactional and repeatable SQLite schema v1 -> v2 migration."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (1, 2):
            raise RuntimeError("Unsupported database version for planner migration")
        db.execute("""
            CREATE TABLE IF NOT EXISTS daily_energy (
                day TEXT PRIMARY KEY,
                starting_energy INTEGER NOT NULL CHECK(starting_energy BETWEEN 0 AND 100),
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS planned_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_day TEXT NOT NULL,
                scheduled_time TEXT,
                activity_name TEXT NOT NULL,
                expected_delta INTEGER CHECK(expected_delta BETWEEN -100 AND 100),
                status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','completed')),
                linked_entry_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_plans_date ON planned_activities(scheduled_day, scheduled_time, id)")
        if version == 1:
            db.execute("PRAGMA user_version=2")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_name(text: str) -> str:
    text = " ".join(text.strip().split())
    if not 1 <= len(text) <= 120:
        raise HTTPException(422, "Activity name must contain 1–120 characters.")
    return text


def clean_time(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError as exc:
        raise HTTPException(422, "Time must be HH:MM.") from exc
    return text


def clean_delta(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise HTTPException(422, "Estimate must be an integer from -100 to 100.") from exc
    if not -100 <= value <= 100:
        raise HTTPException(422, "Estimate must be between -100 and 100.")
    return value


def estimate_stats() -> dict[str, dict]:
    """Group activity names case-insensitively; raw observation distributions only."""
    with connect() as db:
        rows = db.execute(
            "SELECT activity_name, energy_before, energy_after FROM entries ORDER BY id"
        ).fetchall()
    grouped = {}
    for row in rows:
        key = row["activity_name"].strip().casefold()
        if not key:
            continue
        if key not in grouped:
            grouped[key] = {"name": row["activity_name"].strip(), "values": []}
        grouped[key]["values"].append(row["energy_after"] - row["energy_before"])
    result = {}
    for key, item in grouped.items():
        values = item["values"]
        value = median(values)
        result[key] = {
            "name": item["name"], "count": len(values), "median": int(value) if value == int(value) else value,
            "min": min(values), "max": max(values),
        }
    return result


def all_plans_for(start: date, end: date) -> list[dict]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM planned_activities WHERE scheduled_day >= ? AND scheduled_day < ? "
            "ORDER BY scheduled_day, scheduled_time IS NULL, scheduled_time, id",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return [dict(row) for row in rows]


def week_data(selected: date) -> tuple[date, list[dict]]:
    monday = selected - timedelta(days=selected.weekday())
    last = monday + timedelta(days=7)
    first_utc, _ = date_bounds(monday)
    final_utc, _ = date_bounds(last)
    with connect() as db:
        energies = {
            row["day"]: row["starting_energy"]
            for row in db.execute(
                "SELECT day, starting_energy FROM daily_energy WHERE day>=? AND day<?",
                (monday.isoformat(), last.isoformat()),
            )
        }
        records = db.execute(
            "SELECT * FROM entries WHERE occurred_at>=? AND occurred_at<? ORDER BY occurred_at",
            (first_utc, final_utc),
        ).fetchall()
    plans = all_plans_for(monday, last)
    stats = estimate_stats()
    days = [
        {"date": (monday + timedelta(days=i)).isoformat(),
         "weekday": i, "energy": energies.get((monday + timedelta(days=i)).isoformat()),
         "records": [], "plans": []}
        for i in range(7)
    ]
    by_day = {item["date"]: item for item in days}
    for record in records:
        key = local_time(record["occurred_at"]).date().isoformat()
        if key in by_day:
            by_day[key]["records"].append({
                "activity_name": record["activity_name"],
                "id": record["id"],
                "display_time": local_time(record["occurred_at"]).strftime("%H:%M"),
                "before": record["energy_before"],
                "after": record["energy_after"],
                "delta": record["energy_after"] - record["energy_before"],
            })
    for plan in plans:
        if plan["status"] == "completed":
            continue  # already appears once as a recorded diary entry
        summary = dict(plan)
        stats_for_name = stats.get(plan["activity_name"].casefold())
        summary["suggested"] = (
            plan["expected_delta"] if plan["expected_delta"] is not None
            else stats_for_name["median"] if stats_for_name else None
        )
        summary["estimate_count"] = stats_for_name["count"] if stats_for_name else 0
        by_day[plan["scheduled_day"]]["plans"].append(summary)
    return monday, days


def calendar_slot(time_text: str) -> str:
    """Round down to a 30-minute display slot; preserve the actual event time."""
    hour, minute = (int(part) for part in time_text.split(":"))
    return f"{hour:02d}:{(minute // 30) * 30:02d}"


def calendar_week(days: list[dict]) -> tuple[list[str], list[dict]]:
    """Arrange existing plans and real diary entries on a 7x48 timetable.

    No writes, date changes, energy assumptions or duplicate completion records.
    Untimed plans are kept separately rather than assigned a fictional hour.
    """
    slots = [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)]
    for day in days:
        day["slots"] = {slot: [] for slot in slots}
        day["untimed"] = []
        for entry in day["records"]:
            day["slots"][calendar_slot(entry["display_time"])].append({
                "kind": "recorded", "name": entry["activity_name"],
                "id": entry["id"], "time": entry["display_time"],
                "delta": entry["delta"],
                "before": entry["before"], "after": entry["after"],
            })
        for plan in day["plans"]:
            event = {
                "kind": "planned", "name": plan["activity_name"],
                "id": plan["id"], "time": plan["scheduled_time"],
                "delta": plan["suggested"],
            }
            if plan["scheduled_time"]:
                day["slots"][calendar_slot(plan["scheduled_time"])].append(event)
            else:
                day["untimed"].append(event)
        for events in day["slots"].values():
            events.sort(key=lambda event: (event["time"], event["kind"]))
    return slots, days


def get_plan(plan_id: int) -> dict:
    with connect() as db:
        plan = db.execute("SELECT * FROM planned_activities WHERE id=?", (plan_id,)).fetchone()
    if plan is None:
        raise HTTPException(404, "Planned activity not found.")
    return dict(plan)


def destination(day: str, view: str = "day") -> str:
    return ("/planner/week?week=" if view == "week" else "/planner/day?day=") + day


@router.get("/week")
def week_page(request: Request, week: str | None = None):
    if response := require_login(request):
        return response
    monday, days = week_data(parsed_day(week))
    slots, days = calendar_week(days)
    return templates.TemplateResponse(
        request=request, name="planner/week.html",
        context={
            "csrf": csrf(request), "monday": monday.isoformat(), "days": days,
            "slots": slots,
            "previous_week": (monday - timedelta(days=7)).isoformat(),
            "next_week": (monday + timedelta(days=7)).isoformat(),
        },
    )


@router.get("/day")
def day_page(request: Request, day: str | None = None, edit_plan: int | None = None, time: str | None = None):
    if response := require_login(request):
        return response
    date_value = parsed_day(day)
    key = date_value.isoformat()
    with connect() as db:
        row = db.execute("SELECT starting_energy FROM daily_energy WHERE day=?", (key,)).fetchone()
    plans = all_plans_for(date_value, date_value + timedelta(days=1))
    stats = estimate_stats()
    for plan in plans:
        stat = stats.get(plan["activity_name"].casefold())
        plan["suggested"] = (
            plan["expected_delta"] if plan["expected_delta"] is not None
            else stat["median"] if stat else None
        )
        plan["estimate_count"] = stat["count"] if stat else 0
    editing = None
    if edit_plan is not None:
        editing = get_plan(edit_plan)
        if editing["scheduled_day"] != key or editing["status"] != "planned":
            raise HTTPException(404, "Editable planned activity not found for this day.")
    return templates.TemplateResponse(
        request=request, name="planner/day.html",
        context={
            "csrf": csrf(request), "day": key, "energy": row["starting_energy"] if row else None,
            "plans": plans, "entries": list(reversed(activity_rows(date_value))),
            "editing": editing, "now_time": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"),
            "selected_time": clean_time(time) if time is not None else None,
        },
    )


@router.post("/energy")
def save_energy(
    request: Request,
    day: str = Form(...), starting_energy: str = Form(""),
    view: str = Form("day"), token: str = Form(...),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    level = starting_energy.strip()
    with connect() as db:
        if level == "":
            db.execute("DELETE FROM daily_energy WHERE day=?", (selected.isoformat(),))
        else:
            try:
                number = int(level)
            except ValueError as exc:
                raise HTTPException(422, "Energy must be between 0 and 100.") from exc
            if not (0 <= number <= 100):
                raise HTTPException(422, "Energy must be between 0 and 100.")
            db.execute(
                "INSERT INTO daily_energy(day,starting_energy,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(day) DO UPDATE SET starting_energy=excluded.starting_energy, "
                "updated_at=excluded.updated_at",
                (selected.isoformat(), number, now_utc()),
            )
    return RedirectResponse(destination(selected.isoformat(), view), status_code=303)


@router.post("/plans")
def create_plan(
    request: Request,
    day: str = Form(...), activity_name: str = Form(...),
    planned_time: str = Form(""), expected_delta: str = Form(""),
    view: str = Form("day"), token: str = Form(...),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    with connect() as db:
        db.execute(
            "INSERT INTO planned_activities(scheduled_day,scheduled_time,activity_name,expected_delta,created_at) "
            "VALUES(?,?,?,?,?)",
            (selected.isoformat(), clean_time(planned_time), clean_name(activity_name),
             clean_delta(expected_delta), now_utc()),
        )
    return RedirectResponse(destination(selected.isoformat(), "week" if view == "week" else "day"), status_code=303)


@router.post("/plans/{plan_id}/edit")
def modify_plan(
    request: Request, plan_id: int, day: str = Form(...), activity_name: str = Form(...),
    planned_time: str = Form(""), expected_delta: str = Form(""), token: str = Form(...),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    name, when, delta = clean_name(activity_name), clean_time(planned_time), clean_delta(expected_delta)
    with connect() as db:
        result = db.execute(
            "UPDATE planned_activities SET scheduled_day=?,scheduled_time=?,activity_name=?,expected_delta=? "
            "WHERE id=? AND status='planned'",
            (selected.isoformat(), when, name, delta, plan_id),
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Editable plan not found.")
    return RedirectResponse(destination(selected.isoformat()), status_code=303)


@router.post("/plans/{plan_id}/delete")
def delete_plan(request: Request, plan_id: int, token: str = Form(...)):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = get_plan(plan_id)
    with connect() as db:
        db.execute("DELETE FROM planned_activities WHERE id=?", (plan_id,))
    return RedirectResponse(destination(selected["scheduled_day"]), status_code=303)


@router.post("/plans/{plan_id}/complete")
def complete_plan(
    request: Request, plan_id: int,
    energy_before: int = Form(...), energy_after: int = Form(...),
    occurred_at: str = Form(...), token: str = Form(...),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM planned_activities WHERE id=? AND status='planned'", (plan_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(409, "Plan already completed or no longer exists.")
        name, before, after, observed = parse_entry(
            row["activity_name"], energy_before, energy_after, occurred_at
        )
        cursor = db.execute(
            "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at) "
            "VALUES(?,?,?,?,?)", (name, before, after, observed, now_utc()),
        )
        db.execute(
            "UPDATE planned_activities SET status='completed',linked_entry_id=? WHERE id=?",
            (cursor.lastrowid, plan_id),
        )
    return RedirectResponse(destination(local_time(observed).date().isoformat()), status_code=303)


@router.get("/insights")
def insights_page(request: Request):
    if response := require_login(request):
        return response
    stats = sorted(estimate_stats().values(), key=lambda v: (-v["count"], v["name"].casefold()))
    return templates.TemplateResponse(
        request=request, name="planner/insights.html",
        context={"csrf": csrf(request), "statistics": stats},
    )
