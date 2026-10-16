"""Optional weekly planner, daily starting energy, and simple diary insights."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from statistics import median

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .main import (
    TZ, activity_rows, check_csrf, connect, date_bounds, local_time, parse_entry,
    parsed_day, require_login, templates, csrf, suggestions,
)

router = APIRouter(prefix="/planner")


def initialize_planner_database() -> None:
    """Transactional migration from older databases up to v6."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (1, 2, 3, 4, 5, 6):
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
        if version < 3:
            existing_plans = {row["name"] for row in db.execute("PRAGMA table_info(planned_activities)")}
            existing_entries = {row["name"] for row in db.execute("PRAGMA table_info(entries)")}
            if "end_time" not in existing_plans:
                db.execute("ALTER TABLE planned_activities ADD COLUMN end_time TEXT")
            if "ended_at" not in existing_entries:
                db.execute("ALTER TABLE entries ADD COLUMN ended_at TEXT")
            db.execute("PRAGMA user_version=3")
    from .recurrence import init_recurrence_db
    init_recurrence_db()
    from .preferences import init_preferences
    init_preferences()
    # Index samples from Add Activity must not become calendar events or
    # reduce the actual energy left on a day.
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("PRAGMA user_version").fetchone()[0]
        if current == 5:
            fields = {row["name"] for row in db.execute("PRAGMA table_info(entries)")}
            if "calendar_visible" not in fields:
                db.execute("ALTER TABLE entries ADD COLUMN calendar_visible INTEGER NOT NULL DEFAULT 0 "
                           "CHECK(calendar_visible IN (0,1))")
            # Old linked plan completions definitely originated from the calendar.
            db.execute("UPDATE entries SET calendar_visible=1 WHERE id IN "
                       "(SELECT linked_entry_id FROM planned_activities "
                       "WHERE linked_entry_id IS NOT NULL)")
            db.execute("UPDATE entries SET calendar_visible=1 WHERE id IN "
                       "(SELECT linked_entry_id FROM recurring_exceptions "
                       "WHERE linked_entry_id IS NOT NULL AND action='completed')")
            db.execute("CREATE INDEX IF NOT EXISTS idx_entries_calendar "
                       "ON entries(calendar_visible,occurred_at)")
            db.execute("PRAGMA user_version=6")
        elif current != 6:
            raise RuntimeError("Expected database schema v5 or v6 after preferences migration")


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


def minute_of_day(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def clean_interval(start_text: str, end_text: str) -> tuple[str | None, str | None]:
    """End time is optional for legacy unscheduled plans. Ranges stay within a day."""
    start, end = clean_time(start_text), clean_time(end_text)
    if end and not start:
        raise HTTPException(422, "An end time requires a start time.")
    if start and end and minute_of_day(end) <= minute_of_day(start):
        raise HTTPException(422, "End time must be later than start time.")
    return start, end


def actual_end(start_utc: str, end_local: str) -> str | None:
    if not end_local.strip():
        return None
    start = local_time(start_utc)
    try:
        end = datetime.strptime(end_local, "%Y-%m-%dT%H:%M").replace(tzinfo=TZ)
    except ValueError as exc:
        raise HTTPException(422, "Invalid actual ending date/time.") from exc
    if end.date() != start.date() or end <= start:
        raise HTTPException(422, "Actual end must be later, on the same day.")
    return end.astimezone(timezone.utc).isoformat()


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
    from .recurrence import recurring_plans
    return [{**dict(row), "recurring": False} for row in rows] + recurring_plans(start, end)


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
            "SELECT * FROM entries WHERE calendar_visible=1 AND occurred_at>=? AND occurred_at<? ORDER BY occurred_at",
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
                "end_time": local_time(record["ended_at"]).strftime("%H:%M") if record["ended_at"] else None,
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


def daily_energy_projection(day: dict) -> dict:
    """Personal planning arithmetic; never infer a missing activity's energy cost.

    Completed plans have already been excluded from day['plans'] by week_data,
    so their diary entries contribute exactly once. Negative totals intentionally
    remain negative, making an overfull day visible rather than hiding the deficit.
    """
    net = sum(item["delta"] for item in day["records"])
    estimated = 0
    unknown = 0
    for plan in day["plans"]:
        delta = plan["suggested"]
        if delta is None:
            unknown += 1
        else:
            net += delta
            estimated += 1
    starting = day["energy"]
    remaining = round(starting + net, 1) if starting is not None else None
    return {
        "net": round(net, 1),
        "remaining": remaining,
        "estimated_count": estimated,
        "unknown_count": unknown,
        "is_estimate": estimated > 0 or unknown > 0,
    }


def calendar_slot(time_text: str) -> str:
    minute = minute_of_day(time_text)
    return f"{minute // 60:02d}:{(minute % 60 // 30) * 30:02d}"


def calendar_week(days: list[dict], start_hour: int = 6, end_hour: int = 23) -> tuple[list[str], list[dict]]:
    """Visual half-hour grid; keep precise times in storage and event labels.

    One event spans multiple slots rather than creating copies. Overlaps share
    available width. Untimed events appear above the timetable.
    """
    slots = [f"{hour:02d}:{minute:02d}" for hour in range(start_hour, end_hour) for minute in (0, 30)]
    for day in days:
        day["slots"] = {slot: [] for slot in slots}
        day["untimed"] = []
        timed = []
        for record in day["records"]:
            timed.append({
                "kind": "recorded", "name": record["activity_name"],
                "id": record["id"], "time": record["display_time"],
                "end_time": record["end_time"], "delta": record["delta"],
                "before": record["before"], "after": record["after"],
            })
        for plan in day["plans"]:
            event = {
                "kind": "planned", "name": plan["activity_name"],
                "id": plan["id"], "time": plan["scheduled_time"],
                "end_time": plan["end_time"], "delta": plan["suggested"],
                "recurring": plan.get("recurring", False),
                "explicit_delta": plan["expected_delta"],
            }
            if event["time"] is None:
                day["untimed"].append(event)
            else:
                timed.append(event)
        for event in timed:
            start_min = minute_of_day(event["time"])
            end_min = minute_of_day(event["end_time"]) if event["end_time"] else start_min + 30
            first_visible = start_hour * 60
            last_visible = end_hour * 60
            if start_min >= last_visible or end_min <= first_visible:
                day["untimed"].append(event)
                continue
            beginning = max(0, start_min // 30 - start_hour * 2)
            ending = min(len(slots), max(beginning + 1, (end_min + 29) // 30 - start_hour * 2))
            event["start_min"] = beginning * 30
            event["end_min"] = ending * 30
            event["span_slots"] = ending - beginning
            event["slot"] = slots[beginning]
        timed = [event for event in timed if "slot" in event]
        timed.sort(key=lambda e: (e["start_min"], e["end_min"], e["kind"], e["id"]))

        def assign_group(group: list[dict]) -> None:
            occupied: list[int] = []
            for event in group:
                lane = next((i for i, finish in enumerate(occupied) if finish <= event["start_min"]), None)
                if lane is None:
                    lane = len(occupied)
                    occupied.append(event["end_min"])
                else:
                    occupied[lane] = event["end_min"]
                event["lane"] = lane
            for event in group:
                event["columns"] = len(occupied)

        group: list[dict] = []
        max_end = -1
        for event in timed:
            if group and event["start_min"] >= max_end:
                assign_group(group)
                group = []
            group.append(event)
            max_end = max(max_end, event["end_min"])
        if group:
            assign_group(group)
        for event in timed:
            day["slots"][event["slot"]].append(event)
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
    from .preferences import load_preferences, energy_class
    prefs = load_preferences()
    monday, days = week_data(parsed_day(week))
    for d in days:
        d["projection"] = daily_energy_projection(d)
    slots, days = calendar_week(days, prefs["day_start"], prefs["day_end"])
    for d in days:
        for events in d["slots"].values():
            for event in events:
                event["energy_class"] = energy_class(event["delta"], prefs)
                event["estimated"] = event["kind"] == "planned"
        for event in d["untimed"]:
            event["energy_class"] = energy_class(event["delta"], prefs)
    return templates.TemplateResponse(
        request=request, name="planner/week.html",
        context={
            "csrf": csrf(request), "monday": monday.isoformat(), "days": days,
            "slots": slots,
            "suggestions": suggestions(), "prefs": prefs,
            "previous_week": (monday - timedelta(days=7)).isoformat(),
            "next_week": (monday + timedelta(days=7)).isoformat(),
        },
    )


@router.get("/day")
def day_page(request: Request, day: str | None = None, edit_plan: int | None = None, edit_recurring: int | None = None, time: str | None = None):
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
    if edit_recurring is not None:
        from .recurrence import occurrence_plan
        editing = occurrence_plan(edit_recurring, date_value)
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
    planned_time: str = Form(""), end_time: str = Form(""),
    expected_delta: str = Form(""), view: str = Form("day"),
    token: str = Form(...),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    start, end = clean_interval(planned_time, end_time)
    name, estimate = clean_name(activity_name), clean_delta(expected_delta)
    with connect() as db:
        db.execute(
            "INSERT INTO planned_activities(scheduled_day,scheduled_time,end_time,activity_name,expected_delta,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (selected.isoformat(), start, end, name, estimate, now_utc()),
        )
    return RedirectResponse(destination(selected.isoformat(), "week" if view == "week" else "day"), status_code=303)


@router.post("/plans/{plan_id}/edit")
def modify_plan(
    request: Request, plan_id: int, day: str = Form(...), activity_name: str = Form(...),
    planned_time: str = Form(""), end_time: str = Form(""),
    expected_delta: str = Form(""), token: str = Form(...),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    name, delta = clean_name(activity_name), clean_delta(expected_delta)
    when, ending = clean_interval(planned_time, end_time)
    with connect() as db:
        result = db.execute(
            "UPDATE planned_activities SET scheduled_day=?,scheduled_time=?,end_time=?,activity_name=?,expected_delta=? "
            "WHERE id=? AND status='planned'",
            (selected.isoformat(), when, ending, name, delta, plan_id),
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
    occurred_at: str = Form(...), ended_at: str = Form(""), token: str = Form(...),
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
        actual_ending = actual_end(observed, ended_at)
        cursor = db.execute(
            "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at,ended_at,calendar_visible) "
            "VALUES(?,?,?,?,?,?,1)", (name, before, after, observed, now_utc(), actual_ending),
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


@router.post("/create")
def create_from_timetable(
    request: Request, day: str = Form(...),
    activity_name: str = Form(...), planned_time: str = Form(...),
    end_time: str = Form(""), expected_delta: str = Form(""),
    mode: str = Form("planned"), energy_before: str = Form(""),
    energy_after: str = Form(""), token: str = Form(...),
):
    """One simple calendar form: plan ahead OR record before/after readings.

    Planned records never masquerade as observations. A completed record is
    stored in the same diary used by the existing activity tracker.
    """
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    name = clean_name(activity_name)
    start, end = clean_interval(planned_time, end_time)
    if start is None:
        raise HTTPException(422, "Choose a start time.")
    if mode not in ("planned", "completed"):
        raise HTTPException(422, "Invalid activity mode.")
    if mode == "planned":
        estimate = clean_delta(expected_delta)
        with connect() as db:
            db.execute(
                "INSERT INTO planned_activities(scheduled_day,scheduled_time,end_time,activity_name,expected_delta,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (selected.isoformat(), start, end, name, estimate, now_utc()),
            )
    else:
        try:
            before, after = int(energy_before), int(energy_after)
        except ValueError as exc:
            raise HTTPException(422, "Enter both actual energy readings.") from exc
        _, before, after, observed = parse_entry(
            name, before, after, f"{selected.isoformat()}T{start}"
        )
        observed_end = actual_end(
            observed, f"{selected.isoformat()}T{end}" if end else ""
        )
        with connect() as db:
            db.execute(
                "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at,ended_at,calendar_visible) "
                "VALUES(?,?,?,?,?,?,1)",
                (name, before, after, observed, now_utc(), observed_end),
            )
    return RedirectResponse(destination(selected.isoformat(), "week"), status_code=303)


from .calendar_actions import router as calendar_actions_router
router.include_router(calendar_actions_router)
from .settings_routes import router as settings_router
router.include_router(settings_router)
