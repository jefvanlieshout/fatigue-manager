"""Tests for the planner and bilingual interface. Run locally: python -m pytest -q."""
import re
from datetime import date

from fastapi.testclient import TestClient

from app import main
from app.i18n import LANGUAGES
from app.planner import estimate_stats, week_data

PASSWORD = "test-password-123"


def signed_in_client(tmp_path):
    main.DB_PATH = tmp_path / "planner-test.sqlite3"
    main.PASSWORD_HASH = main.hash_password(PASSWORD)
    client = TestClient(main.app)
    client.__enter__()
    html = client.get("/login").text
    token = re.search(r'name="token" value="([^"]+)"', html).group(1)
    r = client.post("/login", data={"password": PASSWORD, "token": token}, follow_redirects=False)
    assert r.status_code == 303
    html = client.get("/").text
    token = re.search(r'name="token" value="([^"]+)"', html).group(1)
    return client, token


def test_migration_to_v3_preserves_existing_entries(tmp_path):
    main.DB_PATH = tmp_path / "migration.sqlite3"
    main.init_db()
    with main.connect() as db:
        db.execute(
            "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at)"
            " VALUES(?,?,?,?,?)",
            ("Original", 80, 70, "2026-10-13T09:00:00+00:00", "2026-10-13T09:00:00+00:00"),
        )
    from app.planner import initialize_planner_database
    initialize_planner_database()
    initialize_planner_database()
    with main.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 6
        assert db.execute("SELECT activity_name FROM entries").fetchone()[0] == "Original"


def test_week_energy_and_completion_workflow(tmp_path):
    client, csrf = signed_in_client(tmp_path)
    try:
        assert "Weekly planner" in client.get("/planner/week?week=2026-10-13").text
        assert "Monday" in client.get("/planner/week?week=2026-10-13").text
        assert client.post("/planner/energy", data={
            "token": csrf, "day": "2026-10-13", "starting_energy": "0", "view": "week"
        }, follow_redirects=False).status_code == 303
        assert "0" in client.get("/planner/day?day=2026-10-13").text
        with main.connect() as db:
            assert db.execute(
                "SELECT starting_energy FROM daily_energy WHERE day='2026-10-13'"
            ).fetchone()[0] == 0
        assert client.post("/planner/plans", data={
            "token": csrf, "day": "2026-10-13", "activity_name": "Cooking",
            "planned_time": "11:00", "expected_delta": "-20"
        }, follow_redirects=False).status_code == 303
        with main.connect() as db:
            plan_id = db.execute("SELECT id FROM planned_activities").fetchone()[0]
        page = client.get("/planner/day?day=2026-10-13")
        assert page.status_code == 200
        assert "Cooking" in page.text
        done = client.post(f"/planner/plans/{plan_id}/complete", data={
            "token": csrf, "energy_before": "70", "energy_after": "45",
            "occurred_at": "2026-10-13T12:30"
        }, follow_redirects=False)
        assert done.status_code == 303
        with main.connect() as db:
            assert db.execute("SELECT count(*) FROM entries").fetchone()[0] == 1
            assert db.execute(
                "SELECT status FROM planned_activities WHERE id=?", (plan_id,)
            ).fetchone()[0] == "completed"
        again = client.post(f"/planner/plans/{plan_id}/complete", data={
            "token": csrf, "energy_before": "70", "energy_after": "45",
            "occurred_at": "2026-10-13T12:30"
        }, follow_redirects=False)
        assert again.status_code == 409
        with main.connect() as db:
            assert db.execute("SELECT count(*) FROM entries").fetchone()[0] == 1
        assert estimate_stats()["cooking"]["median"] == -25
        assert "Cooking" in client.get("/planner/insights").text
        with main.connect() as db:
            entry_id = db.execute("SELECT id FROM entries").fetchone()[0]
        assert client.post(f"/entries/{entry_id}/delete", data={
            "token": csrf
        }, follow_redirects=False).status_code == 303
        with main.connect() as db:
            assert db.execute(
                "SELECT status,linked_entry_id FROM planned_activities WHERE id=?", (plan_id,)
            ).fetchone()[:] == ("planned", None)
    finally:
        client.__exit__(None, None, None)


def test_blank_energy_is_missing_not_zero(tmp_path):
    client, token = signed_in_client(tmp_path)
    try:
        for value in ["0", ""]:
            assert client.post("/planner/energy", data={
                "day": "2026-10-13", "starting_energy": value, "token": token
            }, follow_redirects=False).status_code == 303
        with main.connect() as db:
            assert db.execute("SELECT count(*) FROM daily_energy").fetchone()[0] == 0
        bad = client.post("/planner/energy", data={
            "day": "2026-10-13", "starting_energy": "101", "token": token
        })
        assert bad.status_code == 422
        assert client.post("/planner/plans", data={
            "day": "2026-10-13", "activity_name": "Walk",
            "expected_delta": "-105", "token": token
        }).status_code == 422
        with main.connect() as db:
            assert db.execute("SELECT count(*) FROM planned_activities").fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_languages_and_unauthorized_access(tmp_path):
    main.DB_PATH = tmp_path / "lang.sqlite3"
    main.PASSWORD_HASH = main.hash_password(PASSWORD)
    with TestClient(main.app) as client:
        page = client.get("/login")
        assert "Good to see you." in page.text
        token = re.search(r'name="token" value="([^"]+)"', page.text).group(1)
        assert client.get("/planner/week", follow_redirects=False).status_code == 303
        assert client.get("/planner/insights", follow_redirects=False).status_code == 303
        switched = client.post("/language", data={
            "token": token, "lang": "nl", "return_to": "/login"
        }, follow_redirects=True)
        assert "Goed je te zien." in switched.text
        assert client.post("/language", data={
            "token": "invalid", "lang": "en"
        }).status_code == 403


def test_translation_keys_match():
    assert set(LANGUAGES["en"]) == set(LANGUAGES["nl"])
    for key in LANGUAGES["en"]:
        assert isinstance(LANGUAGES["en"][key], type(LANGUAGES["nl"][key]))
    assert len(LANGUAGES["en"]["days"]) == 7


def test_week_starts_monday(tmp_path):
    main.DB_PATH = tmp_path / "week.sqlite3"
    main.init_db()
    from app.planner import initialize_planner_database
    initialize_planner_database()
    monday, days = week_data(date(2026, 10, 13))
    assert monday == date(2026, 10, 12)
    assert days[0]["date"] == "2026-10-12"
    assert days[-1]["date"] == "2026-10-18"
