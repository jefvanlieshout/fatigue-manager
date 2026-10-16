"""Simple in-calendar edit/delete/complete actions for diary, plans and recurrences."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from .main import check_csrf, connect, local_time, parse_entry, parsed_day, require_login
from .planner import actual_end, clean_delta, clean_interval, clean_name, destination, now_utc
from .recurrence import (
    assert_occurrence, occurrence_plan, parse_repeat, read_rule, write_exception,
)

router = APIRouter()


@router.post("/calendar-event")
def calendar_event(
    request: Request,
    token: str = Form(...),
    event_kind: str = Form("new"),
    event_id: int = Form(0),
    operation: str = Form("save"),
    day: str = Form(...),
    activity_name: str = Form(""),
    planned_time: str = Form(""),
    end_time: str = Form(""),
    mode: str = Form("planned"),
    energy_before: str = Form(""),
    energy_after: str = Form(""),
    expected_delta: str = Form(""),
    repeat: str = Form("none"),
    repeat_until: str = Form(""),
    repeat_days: list[str] = Form([]),
):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(day)
    day_text = selected.isoformat()

    if event_kind not in ("new", "planned", "recorded", "recurring"):
        raise HTTPException(422, "Invalid calendar event type.")
    if operation not in ("save", "delete_one", "delete_series"):
        raise HTTPException(422, "Invalid operation.")
    if event_kind == "new" and operation != "save":
        raise HTTPException(422, "Cannot delete an unsaved activity.")
    if event_kind != "recurring" and operation == "delete_series":
        raise HTTPException(422, "Only repeating series can be deleted together.")
    if event_kind != "new" and event_id <= 0:
        raise HTTPException(422, "Activity ID required.")

    if operation != "save":
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if event_kind == "recurring":
                rule = read_rule(db, event_id)
                if operation == "delete_series":
                    db.execute("DELETE FROM recurring_rules WHERE id=?", (event_id,))
                else:
                    assert_occurrence(rule, selected)
                    write_exception(db, event_id, selected, "skipped")
            elif event_kind == "planned":
                result = db.execute(
                    "DELETE FROM planned_activities WHERE id=? AND status='planned'", (event_id,)
                )
                if result.rowcount != 1:
                    raise HTTPException(404, "Planned activity not found.")
            else:
                entry = db.execute("SELECT id FROM entries WHERE id=?", (event_id,)).fetchone()
                if not entry:
                    raise HTTPException(404, "Diary activity not found.")
                db.execute(
                    "UPDATE planned_activities SET status='planned',linked_entry_id=NULL "
                    "WHERE linked_entry_id=?", (event_id,)
                )
                db.execute("DELETE FROM recurring_exceptions WHERE linked_entry_id=?", (event_id,))
                db.execute("DELETE FROM entries WHERE id=?", (event_id,))
        return RedirectResponse(destination(day_text, "week"), status_code=303)

    if mode not in ("planned", "completed"):
        raise HTTPException(422, "Invalid mode.")
    if event_kind == "recorded" and mode != "completed":
        raise HTTPException(422, "Recorded activities must retain actual energy.")
    if event_kind != "new" and repeat != "none":
        raise HTTPException(422, "Recurrence can only be chosen when creating a new activity.")
    name = clean_name(activity_name)
    start, ending = clean_interval(planned_time, end_time)
    if start is None:
        raise HTTPException(422, "Start time required.")
    if event_kind == "new" and repeat != "none":
        if mode != "planned":
            raise HTTPException(422, "A recurring rule must be a future plan.")
        if ending is None:
            raise HTTPException(422, "Recurring activities need an end time.")
        weekdays = parse_repeat(repeat, selected, repeat_days)
        until = parsed_day(repeat_until) if repeat_until.strip() else None
        if until is not None and until < selected:
            raise HTTPException(422, "The repeat-until date must not precede the start date.")
        estimate = clean_delta(expected_delta)
        with connect() as db:
            db.execute(
                "INSERT INTO recurring_rules "
                "(activity_name,start_day,until_day,weekdays,scheduled_time,end_time,expected_delta,created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (name, day_text, until.isoformat() if until else None, weekdays,
                 start, ending, estimate, now_utc()),
            )
        return RedirectResponse(destination(day_text, "week"), status_code=303)

    estimate = clean_delta(expected_delta) if mode == "planned" else None
    before = after = observed = observed_end = None
    if mode == "completed":
        try:
            before, after = int(energy_before), int(energy_after)
        except ValueError as exc:
            raise HTTPException(422, "Actual before/after energy is required.") from exc
        _, before, after, observed = parse_entry(
            name, before, after, f"{day_text}T{start}"
        )
        observed_end = actual_end(observed, f"{day_text}T{ending}" if ending else "")

    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if event_kind == "new":
            if mode == "planned":
                db.execute(
                    "INSERT INTO planned_activities "
                    "(activity_name,scheduled_day,scheduled_time,end_time,expected_delta,created_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (name, day_text, start, ending, estimate, now_utc()),
                )
            else:
                db.execute(
                    "INSERT INTO entries "
                    "(activity_name,energy_before,energy_after,occurred_at,ended_at,created_at,calendar_visible) "
                    "VALUES(?,?,?,?,?,?,1)",
                    (name, before, after, observed, observed_end, now_utc()),
                )
        elif event_kind == "recorded":
            existing = db.execute("SELECT id FROM entries WHERE id=?", (event_id,)).fetchone()
            if not existing:
                raise HTTPException(404, "Diary activity not found.")
            db.execute(
                "UPDATE entries SET activity_name=?,energy_before=?,energy_after=?,"
                "occurred_at=?,ended_at=? WHERE id=?",
                (name, before, after, observed, observed_end, event_id),
            )
        elif event_kind == "planned":
            plan = db.execute(
                "SELECT * FROM planned_activities WHERE id=? AND status='planned'",
                (event_id,),
            ).fetchone()
            if plan is None:
                raise HTTPException(409, "This plan was already completed or removed.")
            if mode == "planned":
                db.execute(
                    "UPDATE planned_activities SET activity_name=?,scheduled_day=?,"
                    "scheduled_time=?,end_time=?,expected_delta=? WHERE id=?",
                    (name, day_text, start, ending, estimate, event_id),
                )
            else:
                entry_id = db.execute(
                    "INSERT INTO entries "
                    "(activity_name,energy_before,energy_after,occurred_at,ended_at,created_at,calendar_visible) "
                    "VALUES(?,?,?,?,?,?,1)",
                    (name, before, after, observed, observed_end, now_utc()),
                ).lastrowid
                db.execute(
                    "UPDATE planned_activities SET status='completed',linked_entry_id=? WHERE id=?",
                    (entry_id, event_id),
                )
        else:
            rule = read_rule(db, event_id)
            assert_occurrence(rule, selected)
            exception = db.execute(
                "SELECT action FROM recurring_exceptions WHERE rule_id=? AND occurrence_day=?",
                (event_id, day_text),
            ).fetchone()
            if exception and exception["action"] in ("completed", "skipped"):
                raise HTTPException(409, "This recurrence was already handled.")
            if mode == "planned":
                write_exception(db, event_id, selected, "modified", name, start, ending, estimate)
            else:
                entry_id = db.execute(
                    "INSERT INTO entries "
                    "(activity_name,energy_before,energy_after,occurred_at,ended_at,created_at,calendar_visible) "
                    "VALUES(?,?,?,?,?,?,1)",
                    (name, before, after, observed, observed_end, now_utc()),
                ).lastrowid
                write_exception(
                    db, event_id, selected, "completed",
                    name, start, ending, None, entry_id,
                )
    return RedirectResponse(destination(day_text, "week"), status_code=303)
