"""v0.3: recurring tasks, calendar CRUD, red now line and mobile-first defaults."""
import re
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.planner import all_plans_for, week_data
from app.recurrence import parse_repeat


def signed_in(tmp_path):
    main.DB_PATH = tmp_path / "recurrence.sqlite3"
    main.PASSWORD_HASH = main.hash_password("local-only-password-123")
    client = TestClient(main.app)
    client.__enter__()
    login = client.get("/login").text
    token = re.search(r'name="token" value="([^"]+)"', login).group(1)
    response = client.post("/login", data={
        "password": "local-only-password-123", "token": token,
    }, follow_redirects=False)
    assert response.status_code == 303
    token = re.search(r'name="token" value="([^"]+)"', client.get("/").text).group(1)
    return client, token


def test_v4_migration_does_not_alter_existing_entries(tmp_path):
    main.DB_PATH = tmp_path / "migration.sqlite3"
    main.init_db()
    with main.connect() as db:
        db.execute(
            "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at) "
            "VALUES('Original',90,65,'2026-10-13T08:00:00+00:00','2026-10-13T08:00:00+00:00')"
        )
    from app.planner import initialize_planner_database
    initialize_planner_database()
    initialize_planner_database()
    with main.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        assert db.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
        assert db.execute("SELECT activity_name FROM entries").fetchone()[0] == "Original"
        assert db.execute("SELECT COUNT(*) FROM recurring_rules").fetchone()[0] == 0


def test_repeat_weekdays_custom_and_bounds():
    assert parse_repeat("weekly", date(2026, 10, 13), []) == "1"
    assert parse_repeat("weekdays", date(2026, 10, 13), []) == "0,1,2,3,4"
    assert parse_repeat("custom", date(2026, 10, 13), ["0", "2", "2"]) == "0,2"


def test_daily_series_skip_modify_complete_and_delete(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        response = client.post("/planner/calendar-event", data={
            "token": token, "day": "2026-10-13", "activity_name": "Cooking",
            "planned_time": "17:00", "end_time": "18:00",
            "mode": "planned", "repeat": "daily", "repeat_until": "2026-10-16",
        }, follow_redirects=False)
        assert response.status_code == 303
        with main.connect() as db:
            rule_id = db.execute("SELECT id FROM recurring_rules").fetchone()[0]
            assert db.execute("SELECT COUNT(*) FROM planned_activities").fetchone()[0] == 0
            assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        plans = all_plans_for(date(2026, 10, 13), date(2026, 10, 20))
        assert [p["scheduled_day"] for p in plans if p["recurring"]] == [
            "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"
        ]
        skip = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recurring",
            "event_id": rule_id, "day": "2026-10-14",
            "operation": "delete_one",
        }, follow_redirects=False)
        assert skip.status_code == 303
        plans = all_plans_for(date(2026, 10, 13), date(2026, 10, 20))
        assert "2026-10-14" not in [p["scheduled_day"] for p in plans if p["recurring"]]
        edited = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recurring", "event_id": rule_id,
            "day": "2026-10-15", "operation": "save", "mode": "planned",
            "activity_name": "Short cooking", "planned_time": "18:00",
            "end_time": "18:45", "expected_delta": "-15",
        }, follow_redirects=False)
        assert edited.status_code == 303
        plans = all_plans_for(date(2026, 10, 15), date(2026, 10, 16))
        assert plans[0]["activity_name"] == "Short cooking"
        assert plans[0]["end_time"] == "18:45"
        done = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recurring", "event_id": rule_id,
            "day": "2026-10-13", "operation": "save", "mode": "completed",
            "activity_name": "Cooking", "planned_time": "17:00",
            "end_time": "18:00", "energy_before": "80", "energy_after": "50",
        }, follow_redirects=False)
        assert done.status_code == 303
        assert client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recurring", "event_id": rule_id,
            "day": "2026-10-13", "operation": "save", "mode": "completed",
            "activity_name": "Cooking", "planned_time": "17:00",
            "end_time": "18:00", "energy_before": "80", "energy_after": "50",
        }).status_code == 409
        with main.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
            assert db.execute(
                "SELECT action FROM recurring_exceptions "
                "WHERE rule_id=? AND occurrence_day='2026-10-13'", (rule_id,)
            ).fetchone()[0] == "completed"
        remove_series = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recurring", "event_id": rule_id,
            "day": "2026-10-16", "operation": "delete_series",
        }, follow_redirects=False)
        assert remove_series.status_code == 303
        assert all_plans_for(date(2026, 10, 13), date(2026, 10, 20)) == []
        with main.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM recurring_rules").fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_edit_delete_planned_and_recorded_in_calendar(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        resp = client.post("/planner/calendar-event", data={
            "token": token, "day": "2026-10-13", "activity_name": "Shopping",
            "planned_time": "10:00", "end_time": "11:00", "mode": "planned",
        }, follow_redirects=False)
        assert resp.status_code == 303
        with main.connect() as db:
            plan_id = db.execute("SELECT id FROM planned_activities").fetchone()[0]
        updated = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "planned", "event_id": plan_id,
            "day": "2026-10-13", "activity_name": "Groceries",
            "planned_time": "10:30", "end_time": "12:00", "mode": "planned",
        }, follow_redirects=False)
        assert updated.status_code == 303
        with main.connect() as db:
            assert db.execute("SELECT activity_name FROM planned_activities WHERE id=?", (plan_id,)).fetchone()[0] == "Groceries"
        completed = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "planned", "event_id": plan_id,
            "day": "2026-10-13", "activity_name": "Groceries",
            "planned_time": "10:30", "end_time": "12:00", "mode": "completed",
            "energy_before": "65", "energy_after": "35",
        }, follow_redirects=False)
        assert completed.status_code == 303
        with main.connect() as db:
            entry_id = db.execute("SELECT id FROM entries").fetchone()[0]
        update_recorded = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recorded", "event_id": entry_id,
            "day": "2026-10-13", "activity_name": "Shopping groceries",
            "planned_time": "10:30", "end_time": "12:30", "mode": "completed",
            "energy_before": "65", "energy_after": "30",
        }, follow_redirects=False)
        assert update_recorded.status_code == 303
        deleted = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "recorded", "event_id": entry_id,
            "day": "2026-10-13", "operation": "delete_one",
        }, follow_redirects=False)
        assert deleted.status_code == 303
        with main.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0
            assert db.execute("SELECT status FROM planned_activities WHERE id=?", (plan_id,)).fetchone()[0] == "planned"
    finally:
        client.__exit__(None, None, None)


def test_week_mobile_now_marker_and_zero_default(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        html = client.get("/planner/week?week=2026-10-13").text
        assert html.count('name="starting_energy"') == 7
        assert "Default 0" not in html
        assert 'data-event-kind=' not in html  # empty diary
        css = (Path(__file__).resolve().parents[1] / "app/static/style.css").read_text()
        js = (Path(__file__).resolve().parents[1] / "app/static/app.js").read_text()
        assert ".calendar-now-marker" in css
        assert "moveNowLine" in js
        assert "visibilitychange" in js
        assert ".shell.wide .planner-page .subtle{display:none}" in css
        assert 'name="repeat_days"' in html
        assert 'value="delete_series"' in html
    finally:
        client.__exit__(None, None, None)
