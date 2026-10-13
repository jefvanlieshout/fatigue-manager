"""Regression tests for the 7-day/24-hour interactive weekly timetable."""
import re

import pytest
from fastapi.testclient import TestClient

from app import main
from app.planner import calendar_slot, calendar_week, week_data


@pytest.fixture()
def diary(tmp_path):
    main.DB_PATH = tmp_path / "calendar.sqlite3"
    main.PASSWORD_HASH = main.hash_password("test-only-password-123")
    with TestClient(main.app) as client:
        html = client.get("/login").text
        token = re.search(r'name="token" value="([^"]+)"', html).group(1)
        response = client.post(
            "/login", data={"password": "test-only-password-123", "token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        yield client, token


def test_all_seven_days_and_24_hours_render(diary):
    client, _ = diary
    html = client.get("/planner/week?week=2026-10-14").text
    assert html.count('class="calendar-day-head"') == 7
    assert html.count('class="calendar-cell"') == 48 * 7
    assert 'data-day="2026-10-14" data-time="14:30"' in html
    assert 'data-day="2026-10-18" data-time="23:30"' in html
    assert "00:00" in html and "23:30" in html
    assert "calendar-scroll" in html
    assert 'id="energy-2026-10-12"' in html
    assert 'id="energy-2026-10-18"' in html


def test_click_slot_fallback_preselects_day_and_time(diary):
    client, _ = diary
    page = client.get("/planner/day?day=2026-10-14&time=14:30")
    assert page.status_code == 200
    assert 'name="day" value="2026-10-14"' in page.text or (
        'name="day"' in page.text and 'value="2026-10-14"' in page.text
    )
    assert 'name="planned_time" type="time"' in page.text
    assert 'value="14:30"' in page.text


def test_slot_plan_saves_and_appears_only_on_correct_day(diary):
    client, token = diary
    saved = client.post(
        "/planner/plans",
        data={
            "token": token, "day": "2026-10-14", "planned_time": "14:45",
            "activity_name": "Walk to the park", "expected_delta": "-15",
            "view": "week",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert saved.headers["location"] == "/planner/week?week=2026-10-14"
    monday, days = week_data(__import__("datetime").date(2026, 10, 14))
    slots, days = calendar_week(days)
    assert len(slots) == 48
    assert "Walk to the park" in [
        event["name"] for event in days[2]["slots"]["14:30"]
    ]
    assert all(
        "Walk to the park" not in [event["name"] for es in day["slots"].values() for event in es]
        for day in days if day["date"] != "2026-10-14"
    )
    response = client.get("/planner/week?week=2026-10-14")
    assert "Walk to the park" in response.text
    assert "14:45" in response.text


def test_recorded_and_untimed_items_survive_timetable(diary):
    client, token = diary
    client.post("/planner/plans", data={
        "token": token, "day": "2026-10-14", "activity_name": "A flexible task",
        "planned_time": "", "view": "week",
    })
    client.post("/entries", data={
        "token": token, "activity_name": "Cooking", "energy_before": "80",
        "energy_after": "62", "occurred_at": "2026-10-14T18:20",
    })
    _, days = week_data(__import__("datetime").date(2026, 10, 14))
    _, days = calendar_week(days)
    assert days[2]["untimed"][0]["name"] == "A flexible task"
    assert days[2]["slots"]["18:00"][0]["kind"] == "recorded"
    assert days[2]["slots"]["18:00"][0]["delta"] == -18
    assert calendar_slot("00:00") == "00:00"
    assert calendar_slot("23:59") == "23:30"


def test_day_energy_is_editable_in_the_calendar(diary):
    client, token = diary
    response = client.post("/planner/energy", data={
        "token": token, "day": "2026-10-18",
        "starting_energy": "0", "view": "week",
    }, follow_redirects=False)
    assert response.headers["location"] == "/planner/week?week=2026-10-18"
    html = client.get("/planner/week?week=2026-10-14").text
    assert 'id="energy-2026-10-18"' in html
    assert 'value="0"' in html


def test_planning_requires_login(tmp_path):
    main.DB_PATH = tmp_path / "new.sqlite3"
    main.PASSWORD_HASH = main.hash_password("test-only-password-123")
    with TestClient(main.app) as client:
        response = client.get("/planner/week", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
