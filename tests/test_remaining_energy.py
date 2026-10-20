"""Per-day remaining-energy outlook and regression checks for activity selection."""
import re
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from app import main
from app.planner import week_data, daily_energy_projection

PASSWORD = "test-energy-forecast-only"


def test_client(tmp_path):
    main.DB_PATH = tmp_path / "outlook.sqlite3"
    main.PASSWORD_HASH = main.hash_password(PASSWORD)
    client = TestClient(main.app)
    client.__enter__()
    login = client.get("/login").text
    token = re.search(r'name="token" value="([^"]+)"', login).group(1)
    assert client.post("/login", data={"password": PASSWORD, "token": token},
        follow_redirects=False).status_code == 303
    token = re.search(r'name="token" value="([^"]+)"', client.get("/").text).group(1)
    return client, token


def make_plan(client, token, name, estimate="", day="2026-10-15"):
    response = client.post("/planner/calendar-event", data={
        "token": token, "day": day, "activity_name": name,
        "planned_time": "14:00", "end_time": "15:00",
        "mode": "planned", "expected_delta": estimate,
    }, follow_redirects=False)
    assert response.status_code == 303


def test_remaining_energy_uses_actual_and_planned_once(tmp_path):
    client, token = test_client(tmp_path)
    try:
        assert client.post("/planner/energy", data={
            "token": token, "day": "2026-10-15", "starting_energy": "80",
            "view": "week"
        }, follow_redirects=False).status_code == 303
        assert client.post("/planner/create", data={
            "token": token, "day": "2026-10-15",
            "activity_name": "Breakfast", "planned_time": "08:30",
            "end_time": "09:00", "mode": "completed",
            "energy_before": "80", "energy_after": "65",
        }, follow_redirects=False).status_code == 303
        make_plan(client, token, "Walk", "-25")
        make_plan(client, token, "Rest", "10")
        make_plan(client, token, "Uncertain task")
        _, days = week_data(date(2026, 10, 15))
        result = daily_energy_projection(days[3])
        assert result["remaining"] == 50
        assert result["net"] == -30
        assert result["estimated_count"] == 2
        assert result["unknown_count"] == 1
        assert result["is_estimate"] is True
        html = client.get("/planner/week?week=2026-10-15").text
        assert "50" in html
        assert 'class="remaining-unknown"' not in html
        assert 'class="remaining-value">≈50</span>' in html
        with main.connect() as db:
            walk_id = db.execute(
                "SELECT id FROM planned_activities WHERE activity_name='Walk'"
            ).fetchone()[0]
        done = client.post("/planner/calendar-event", data={
            "token": token, "event_kind": "planned", "event_id": walk_id,
            "day": "2026-10-15", "activity_name": "Walk",
            "planned_time": "14:00", "end_time": "15:00",
            "mode": "completed", "energy_before": "65", "energy_after": "45",
        }, follow_redirects=False)
        assert done.status_code == 303
        _, days = week_data(date(2026, 10, 15))
        result = daily_energy_projection(days[3])
        assert result["remaining"] == 55
        assert result["estimated_count"] == 1
        assert result["unknown_count"] == 1
    finally:
        client.__exit__(None, None, None)


def test_default_zero_is_not_an_observed_start(tmp_path):
    client, token = test_client(tmp_path)
    try:
        make_plan(client, token, "Laundry", "-15")
        _, days = week_data(date(2026, 10, 15))
        summary = daily_energy_projection(days[3])
        assert summary["remaining"] is None
        assert summary["net"] == -15
        html = client.get("/planner/week?week=2026-10-15").text
        assert 'data-saved="0"' in html
        assert 'data-net="-15"' in html
        assert 'class="remaining-value">—' in html or '>—</span>' in html
    finally:
        client.__exit__(None, None, None)


def test_negative_remaining_survives_and_historic_estimates(tmp_path):
    client, token = test_client(tmp_path)
    try:
        assert client.post("/entries", data={
            "token": token, "activity_name": "Vacuuming",
            "energy_before": "70", "energy_after": "50",
            "occurred_at": "2026-10-12T14:00"
        }, follow_redirects=False).status_code == 303
        assert client.post("/planner/energy", data={
            "token": token, "day": "2026-10-15", "starting_energy": "15",
        }, follow_redirects=False).status_code == 303
        make_plan(client, token, "Vacuuming")
        _, days = week_data(date(2026, 10, 15))
        summary = daily_energy_projection(days[3])
        assert summary["remaining"] == -5
        assert summary["unknown_count"] == 0
        assert summary["estimated_count"] == 1
        html = client.get("/planner/week?week=2026-10-15").text
        assert "energy-overbooked" in html
    finally:
        client.__exit__(None, None, None)


def test_picker_does_not_reopen_after_selecting_name():
    root = Path(__file__).resolve().parents[1]
    js = (root / "app/static/app.js").read_text()
    css = (root / "app/static/style.css").read_text()
    week = (root / "app/templates/planner/week.html").read_text()
    assert 'option.addEventListener("pointerdown", event => event.preventDefault())' in js
    assert 'suppressNextFocus = true' in js
    assert 'picker.hidden = true' in js
    assert 'quickForm.addEventListener("submit"' in js
    assert ".activity-name-field{position:relative}" in css
    assert "position:absolute;z-index:60" in css
    assert 'type="button" role="option"' in week
    assert 'aria-autocomplete="list"' in week


def test_morning_energy_rolls_forward_only_within_its_week(tmp_path):
    """Monday seeds seven days; Tuesday changes six, preserving Monday."""
    client, token = test_client(tmp_path)
    try:
        def save(day, value, view="week"):
            return client.post("/planner/energy", data={
                "token": token, "day": day, "starting_energy": str(value),
                "view": view,
            }, follow_redirects=False)

        # A different week must never be affected.
        assert save("2026-10-11", 55).status_code == 303  # Sunday
        monday = save("2026-10-12", 80)
        assert monday.status_code == 303
        assert monday.headers["location"] == "/planner/week?week=2026-10-12"
        _, days = week_data(date(2026, 10, 12))
        assert [d["energy"] for d in days] == [80] * 7

        # Tuesday's new reading changes only Tuesday through Sunday.
        assert save("2026-10-13", 60).status_code == 303
        _, days = week_data(date(2026, 10, 12))
        assert [d["energy"] for d in days] == [80] + [60] * 6

        # The daily outlook and printed calendar use these same values.
        html = client.get("/planner/week?week=2026-10-12").text
        assert 'id="energy-2026-10-12"' in html
        assert 'value="80"' in html
        assert 'id="energy-2026-10-13"' in html
        assert 'value="60"' in html
        printed = client.get("/planner/print?week=2026-10-12").text
        assert "80 left" in printed
        assert "60 left" in printed
        assert "Saving this value also updates" in html
        assert "Saving this value also updates" in client.get(
            "/planner/day?day=2026-10-13"
        ).text

        # A Sunday change updates just Sunday; previous and next weeks stay put.
        assert save("2026-10-18", 35).status_code == 303
        _, days = week_data(date(2026, 10, 12))
        assert [d["energy"] for d in days] == [80] + [60] * 5 + [35]
        with main.connect() as db:
            assert db.execute(
                "SELECT starting_energy FROM daily_energy WHERE day='2026-10-11'"
            ).fetchone()[0] == 55
            assert db.execute(
                "SELECT COUNT(*) FROM daily_energy WHERE day >= '2026-10-19'"
            ).fetchone()[0] == 0
    finally:
        client.__exit__(None, None, None)


def test_clearing_energy_clears_remaining_week_not_previous_days(tmp_path):
    client, token = test_client(tmp_path)
    try:
        def save(day, value):
            return client.post("/planner/energy", data={
                "token": token, "day": day, "starting_energy": value,
            }, follow_redirects=False)

        assert save("2026-10-12", "72").status_code == 303
        assert save("2026-10-13", "").status_code == 303
        _, days = week_data(date(2026, 10, 12))
        assert [d["energy"] for d in days] == [72] + [None] * 6

        # Wrong readings are rejected without altering any saved day.
        for bad in ("-1", "101", "banana"):
            assert save("2026-10-14", bad).status_code == 422
            _, days = week_data(date(2026, 10, 12))
            assert [d["energy"] for d in days] == [72] + [None] * 6

        # The Day Overview uses the same shared save route.
        assert save("2026-10-14", "0").status_code == 303
        _, days = week_data(date(2026, 10, 12))
        assert [d["energy"] for d in days] == [72, None] + [0] * 5
    finally:
        client.__exit__(None, None, None)
