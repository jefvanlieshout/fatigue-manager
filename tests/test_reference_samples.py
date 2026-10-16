"""Index/reference samples are not actual events in the planner (schema v6)."""
import re
from datetime import date

from fastapi.testclient import TestClient
from app import main
from app.planner import week_data, daily_energy_projection, estimate_stats


def signed_in(tmp_path):
    main.DB_PATH = tmp_path / "reference-v6.sqlite3"
    main.PASSWORD_HASH = main.hash_password("test-password-12345")
    client = TestClient(main.app)
    client.__enter__()
    token = re.search(r'name="token" value="([^"]+)"', client.get("/login").text).group(1)
    assert client.post("/login", data={
        "password": "test-password-12345", "token": token
    }, follow_redirects=False).status_code == 303
    token = re.search(r'name="token" value="([^"]+)"', client.get("/").text).group(1)
    return client, token


def test_index_sample_saved_for_estimates_but_never_scheduled(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        client.post("/planner/energy", data={
            "token": token, "day": "2026-10-14", "starting_energy": "80",
            "view": "week"
        }, follow_redirects=False)
        response = client.post("/entries", data={
            "token": token, "activity_name": "Reference laundry",
            "energy_before": "80", "energy_after": "50",
            "occurred_at": "2026-10-14T10:30"
        }, follow_redirects=False)
        assert response.status_code == 303
        with main.connect() as db:
            row = db.execute("SELECT calendar_visible FROM entries WHERE activity_name='Reference laundry'").fetchone()
            assert row["calendar_visible"] == 0
            assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        _, days = week_data(date(2026, 10, 14))
        assert days[2]["records"] == []
        assert daily_energy_projection(days[2])["remaining"] == 80
        assert estimate_stats()["reference laundry"]["median"] == -30
        assert "Reference laundry" in main.suggestions()
        assert "Reference laundry" in client.get("/?day=2026-10-14").text
        # The name IS offered as an autocomplete suggestion, but must not
        # appear as a scheduled calendar event.
        week_html = client.get("/planner/week?week=2026-10-14").text
        assert 'data-activity-name="Reference laundry"' in week_html
        assert 'data-event-name="Reference laundry"' not in week_html
        assert "Reference laundry" not in client.get("/planner/print?week=2026-10-14").text
    finally:
        client.__exit__(None, None, None)


def test_calendar_completed_event_does_appear_and_count(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        client.post("/planner/energy", data={
            "token": token, "day": "2026-10-14", "starting_energy": "80",
        }, follow_redirects=False)
        assert client.post("/planner/calendar-event", data={
            "token": token, "day": "2026-10-14",
            "activity_name": "Actual cooking", "planned_time": "11:00",
            "end_time": "12:00", "mode": "completed",
            "energy_before": "80", "energy_after": "65",
        }, follow_redirects=False).status_code == 303
        with main.connect() as db:
            row = db.execute("SELECT calendar_visible FROM entries WHERE activity_name='Actual cooking'").fetchone()
            assert row["calendar_visible"] == 1
        _, days = week_data(date(2026, 10, 14))
        assert [r["activity_name"] for r in days[2]["records"]] == ["Actual cooking"]
        assert daily_energy_projection(days[2])["remaining"] == 65
        assert "Actual cooking" in client.get("/planner/week?week=2026-10-14").text
        assert "Actual cooking" in client.get("/planner/print?week=2026-10-14").text
        assert "Actual cooking" not in client.get("/?day=2026-10-14").text
    finally:
        client.__exit__(None, None, None)


def test_v5_upgrade_keeps_records_and_backfills_linked_completions(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        # Build v5-style historical content without source classifications.
        with main.connect() as db:
            db.execute("INSERT INTO entries (activity_name,energy_before,energy_after,occurred_at,created_at) "
                       "VALUES ('Historical sample',90,70,'2026-10-14T09:00:00+00:00','2026-10-14T09:00:00+00:00')")
            db.execute("INSERT INTO entries (activity_name,energy_before,energy_after,occurred_at,created_at) "
                       "VALUES ('Linked completion',80,45,'2026-10-14T10:00:00+00:00','2026-10-14T10:00:00+00:00')")
            linked = db.execute("SELECT id FROM entries WHERE activity_name='Linked completion'").fetchone()[0]
            db.execute("INSERT INTO planned_activities(scheduled_day,scheduled_time,activity_name,expected_delta,status,linked_entry_id,created_at) "
                       "VALUES('2026-10-14','12:00','Linked completion',-35,'completed',?,'2026-10-14T08:00:00+00:00')", (linked,))
            db.execute("UPDATE entries SET calendar_visible=0")
            db.execute("PRAGMA user_version=5")
        from app.planner import initialize_planner_database
        initialize_planner_database()
        initialize_planner_database()  # idempotent migration
        with main.connect() as db:
            values = {r["activity_name"]: r["calendar_visible"] for r in db.execute(
                "SELECT activity_name, calendar_visible FROM entries"
            )}
            assert db.execute("PRAGMA user_version").fetchone()[0] == 6
            assert values == {"Historical sample": 0, "Linked completion": 1}
            assert db.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 2
        _, days = week_data(date(2026, 10, 14))
        assert [r["activity_name"] for r in days[2]["records"]] == ["Linked completion"]
    finally:
        client.__exit__(None, None, None)


def test_legend_removed_and_print_header_is_compact(tmp_path):
    client, token = signed_in(tmp_path)
    try:
        week = client.get("/planner/week?week=2026-10-14").text
        assert 'class="calendar-legend"' not in week
        assert "On smaller screens, swipe sideways to see the entire week." not in week
        printed = client.get("/planner/print?week=2026-10-14").text
        assert 'class="print-title"' not in printed
        assert 'class="print-day-name"' in printed
        assert 'class="print-energy-remaining' in printed
        assert "/static/print.css?v=0.2.11" in printed
    finally:
        client.__exit__(None, None, None)
