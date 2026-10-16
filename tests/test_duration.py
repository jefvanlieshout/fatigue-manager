"""Local tests: longer events, drag-selected ranges and direct before/after logging."""
import re
from datetime import date

from fastapi.testclient import TestClient
from app import main
from app.planner import calendar_week, week_data, clean_interval


def authenticated(tmp_path):
    main.DB_PATH = tmp_path / "duration-test.sqlite3"
    main.PASSWORD_HASH = main.hash_password("test-password-12345")
    client = TestClient(main.app)
    client.__enter__()
    login = client.get("/login").text
    csrf = re.search(r'name="token" value="([^"]+)"', login).group(1)
    assert client.post("/login", data={
        "password": "test-password-12345", "token": csrf
    }, follow_redirects=False).status_code == 303
    csrf = re.search(r'name="token" value="([^"]+)"', client.get("/").text).group(1)
    return client, csrf


def test_schema_v3_upgrades_existing_rows(tmp_path):
    main.DB_PATH = tmp_path / "old.sqlite3"
    main.init_db()
    with main.connect() as db:
        db.execute(
            "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at) "
            "VALUES(?,?,?,?,?)",
            ("Legacy", 70, 35, "2026-10-13T09:00:00+00:00",
             "2026-10-13T09:00:00+00:00"),
        )
    from app.planner import initialize_planner_database
    initialize_planner_database()
    initialize_planner_database()  # idempotent
    with main.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        assert "ended_at" in [c["name"] for c in db.execute("PRAGMA table_info(entries)")]
        assert "end_time" in [c["name"] for c in db.execute("PRAGMA table_info(planned_activities)")]
        row = db.execute("SELECT activity_name,energy_before,energy_after,ended_at FROM entries").fetchone()
        assert tuple(row) == ("Legacy", 70, 35, None)


def test_long_plan_one_event_not_five_copies(tmp_path):
    client, token = authenticated(tmp_path)
    try:
        r = client.post("/planner/create", data={
            "token": token, "day": "2026-10-14",
            "activity_name": "Long walk", "planned_time": "10:00",
            "end_time": "12:30", "mode": "planned",
        }, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/planner/week?week=2026-10-14"
        _, days = week_data(date(2026, 10, 14))
        _, days = calendar_week(days)
        events = days[2]["slots"]["10:00"]
        assert len(events) == 1
        assert events[0]["span_slots"] == 5
        assert events[0]["end_time"] == "12:30"
        assert all(not days[2]["slots"][s] for s in ("10:30", "11:00", "11:30", "12:00"))
        assert "Long walk" in client.get("/planner/week?week=2026-10-14").text
        with main.connect() as db:
            assert db.execute("SELECT count(*) FROM entries").fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_direct_record_stores_actual_energy_and_duration(tmp_path):
    client, token = authenticated(tmp_path)
    try:
        r = client.post("/planner/create", data={
            "token": token, "day": "2026-10-14",
            "activity_name": "Cooking", "planned_time": "17:15",
            "end_time": "18:45", "mode": "completed",
            "energy_before": "75", "energy_after": "45",
        }, follow_redirects=False)
        assert r.status_code == 303
        with main.connect() as db:
            row = db.execute("SELECT energy_before,energy_after,ended_at FROM entries").fetchone()
            assert row["energy_before"] == 75
            assert row["energy_after"] == 45
            assert row["ended_at"] is not None
            assert db.execute("SELECT count(*) FROM planned_activities").fetchone()[0] == 0
        _, days = week_data(date(2026, 10, 14))
        _, days = calendar_week(days)
        event = days[2]["slots"]["17:00"][0]
        assert event["kind"] == "recorded"
        assert event["span_slots"] == 4
        assert event["delta"] == -30
    finally:
        client.__exit__(None, None, None)


def test_invalid_or_incomplete_energy_does_not_write(tmp_path):
    client, token = authenticated(tmp_path)
    try:
        for payload in (
            {"mode": "completed", "energy_before": "", "energy_after": "40"},
            {"mode": "completed", "energy_before": "101", "energy_after": "40"},
            {"mode": "planned", "energy_before": "", "energy_after": ""},
        ):
            data = {
                "token": token, "day": "2026-10-14", "activity_name": "Invalid",
                "planned_time": "13:00", "end_time": "12:30", **payload
            }
            assert client.post("/planner/create", data=data).status_code == 422
        with main.connect() as db:
            assert db.execute("SELECT count(*) FROM entries").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM planned_activities").fetchone()[0] == 0
        assert clean_interval("10:00","12:30") == ("10:00", "12:30")
    finally:
        client.__exit__(None, None, None)


def test_overlap_uses_separate_visual_lanes(tmp_path):
    client, token = authenticated(tmp_path)
    try:
        for name, start, end in [("A", "10:00", "12:00"), ("B", "11:00", "12:30")]:
            assert client.post("/planner/create", data={
                "token": token, "day": "2026-10-14", "activity_name": name,
                "planned_time": start, "end_time": end, "mode": "planned",
            }, follow_redirects=False).status_code == 303
        _, days = week_data(date(2026, 10, 14))
        _, days = calendar_week(days)
        a = days[2]["slots"]["10:00"][0]
        b = days[2]["slots"]["11:00"][0]
        assert a["lane"] != b["lane"]
        assert a["columns"] == b["columns"] == 2
    finally:
        client.__exit__(None, None, None)


def test_main_tracker_can_edit_actual_end(tmp_path):
    client, token = authenticated(tmp_path)
    try:
        assert client.post("/entries", data={
            "token": token, "activity_name": "Rest",
            "energy_before": "20", "energy_after": "55",
            "occurred_at": "2026-10-14T14:00", "ended_at": "2026-10-14T15:15",
        }, follow_redirects=False).status_code == 303
        with main.connect() as db:
            row = db.execute("SELECT id,ended_at FROM entries").fetchone()
            assert row["ended_at"] is not None
        page = client.get(f'/entries/{row["id"]}/edit')
        assert 'value="2026-10-14T15:15"' in page.text
    finally:
        client.__exit__(None, None, None)
