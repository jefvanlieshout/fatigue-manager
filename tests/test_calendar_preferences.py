"""Calendar preferences, shared activity lookup, printable week, and security."""
import re
from datetime import date

from fastapi.testclient import TestClient
from app import main
from app.preferences import DEFAULTS, energy_class, validate_preferences, load_preferences
from app.planner import calendar_week, week_data


def login(tmp_path):
    main.DB_PATH = tmp_path / "settings.sqlite3"
    main.PASSWORD_HASH = main.hash_password("test-user-password-123")
    client = TestClient(main.app)
    client.__enter__()
    csrf = re.search(r'name="token" value="([^"]+)"', client.get("/login").text).group(1)
    response = client.post("/login", data={"token": csrf,
        "password": "test-user-password-123"}, follow_redirects=False)
    assert response.status_code == 303
    csrf = re.search(r'name="token" value="([^"]+)"', client.get("/").text).group(1)
    return client, csrf


def test_color_bands_and_validation():
    p = DEFAULTS
    assert energy_class(0, p) == "energy-low"
    assert energy_class(-10, p) == "energy-low"
    assert energy_class(-11, p) == "energy-medium"
    assert energy_class(-20, p) == "energy-medium"
    assert energy_class(-21, p) == "energy-high"
    assert energy_class(-100, p) == "energy-high"
    assert energy_class(25, p) == "energy-restored"
    assert energy_class(None, p) == "energy-unknown"
    values = DEFAULTS.copy()
    values.update(low_max=14, medium_max=28, day_start=8, day_end=21)
    assert validate_preferences(values)["medium_max"] == 28


def test_settings_authentication_and_persistence(tmp_path):
    client, csrf = login(tmp_path)
    try:
        prefs = load_preferences()
        assert (prefs["day_start"], prefs["day_end"]) == (6,23)
        assert (prefs["print_start"], prefs["print_end"]) == (7,22)
        bad = client.post("/planner/settings", data={
            "token": csrf, "week": "2026-10-13", **{**DEFAULTS, "medium_max": 5}
        })
        assert bad.status_code == 422
        assert load_preferences()["medium_max"] == 20
        unauthorized = client.post("/planner/settings", data={
            "token": "wrong", "week": "2026-10-13", **DEFAULTS
        })
        assert unauthorized.status_code == 403
        update = {**DEFAULTS, "low_max": 12, "medium_max": 25,
                  "day_start": 8, "day_end": 21,
                  "print_start": 9, "print_end": 20,
                  "low_color": "#228844"}
        saved = client.post("/planner/settings", data={
            "token": csrf, "week": "2026-10-13", **update
        }, follow_redirects=False)
        assert saved.status_code == 303
        assert load_preferences()["day_start"] == 8
        assert load_preferences()["print_end"] == 20
        assert load_preferences()["low_color"] == "#228844"
        week_html = client.get("/planner/week?week=2026-10-13").text
        assert "08:00" in week_html and "20:30" in week_html
        assert 'data-low-color="#228844"' in week_html
    finally:
        client.__exit__(None, None, None)


def test_print_view_a4_range_and_no_data_leak(tmp_path):
    client, csrf = login(tmp_path)
    try:
        page = client.get("/planner/print?week=2026-10-13")
        assert page.status_code == 200
        assert "07:00" in page.text and "21:30" in page.text
        assert "22:30" not in page.text
        assert 'data-count="30"' in page.text
        assert "/static/print.css" in page.text
        assert client.get("/planner/print?week=2026-10-13", follow_redirects=False).status_code == 200
    finally:
        client.__exit__(None, None, None)


def test_activities_saved_anywhere_are_suggested(tmp_path):
    client, token = login(tmp_path)
    try:
        plan = client.post("/planner/calendar-event", data={
            "token": token, "day": "2026-10-13", "activity_name": "Garden tidy",
            "planned_time": "11:00", "end_time": "12:00", "mode": "planned",
        }, follow_redirects=False)
        assert plan.status_code == 303
        assert "Garden tidy" in main.suggestions()
        assert 'data-activity-name="Garden tidy"' in client.get(
            "/planner/week?week=2026-10-13"
        ).text
        added = client.post("/planner/calendar-event", data={
            "token": token, "day": "2026-10-14", "activity_name": "Laundry",
            "planned_time": "11:00", "end_time": "12:00", "mode": "planned",
            "repeat": "weekly"
        }, follow_redirects=False)
        assert added.status_code == 303
        assert "Laundry" in main.suggestions()
    finally:
        client.__exit__(None, None, None)


def test_ui_markers_gear_and_no_confirm(tmp_path):
    client, token = login(tmp_path)
    try:
        html = client.get("/planner/week?week=2026-10-13").text
        assert 'id="calendar-settings-button"' in html
        assert 'href="/planner/settings?week=2026-10-12"' in html
        assert 'id="calendar-settings"' in html

        assert 'id="energy-drawer"' not in html
        assert html.count('class="calendar-energy-inline"') == 7
        assert html.count('class="battery-symbol"') == 7
        assert html.count('name="starting_energy"') == 7
        assert html.count('class="visually-hidden" tabindex="-1"') == 7
        # Each value sits directly beneath the correct day name, not in a dropdown.
        import re
        headers = re.findall(r'<th scope="col" class="calendar-day-head".*?</th>', html, flags=re.S)
        assert len(headers) == 7
        for header in headers:
            assert '<form method="post" action="/planner/energy"' in header
            assert '<span aria-hidden="true" class="battery-symbol">🔋</span>' in header
            assert 'name="starting_energy"' in header
        assert "Default 0" not in html
        assert 'href="/planner/insights"' not in html
    finally:
        client.__exit__(None, None, None)

def test_gear_opens_settings_as_a_page_without_javascript(tmp_path):
    client, csrf = login(tmp_path)
    try:
        week_html = client.get("/planner/week?week=2026-10-14").text
        assert 'id="calendar-settings-button"' in week_html
        assert 'href="/planner/settings?week=2026-10-12"' in week_html
        assert '<dialog class="calendar-dialog preferences-dialog" id="calendar-settings"' in week_html
        assert "<title>Weekly planner" in week_html or "<title>" in week_html
        settings = client.get("/planner/settings?week=2026-10-14")
        assert settings.status_code == 200
        assert 'action="/planner/settings"' in settings.text
        assert 'name="low_max"' in settings.text
        assert 'name="day_start"' in settings.text
        assert 'name="print_start"' in settings.text
        assert 'name="token"' in settings.text
        assert 'value="2026-10-12"' in settings.text
        js = (__import__("pathlib").Path(__file__).resolve().parents[1] / "app/static/app.js").read_text()
        assert 'event.preventDefault();' in js
        assert 'settingsDialog.showModal()' in js
    finally:
        client.__exit__(None, None, None)


def test_settings_get_requires_login(tmp_path):
    main.DB_PATH = tmp_path / "locked.sqlite3"
    main.PASSWORD_HASH = main.hash_password("test-user-password-123")
    with TestClient(main.app) as client:
        response = client.get("/planner/settings?week=2026-10-14", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


def test_print_week_shows_same_daily_remaining_energy_as_calendar(tmp_path):
    """A4 header includes the whole-day forecast, even outside print hours."""
    client, token = login(tmp_path)
    try:
        # Wednesday: starting 80, actual breakfast -10 outside 07:00 print
        # window, planned walk -25, and a calendar-only appointment with
        # unknown energy. The final estimate should be 45, NOT 55 or 20.
        saved = client.post("/planner/energy", data={
            "token": token, "day": "2026-10-14",
            "starting_energy": "80", "view": "week",
        }, follow_redirects=False)
        assert saved.status_code == 303
        recorded = client.post("/planner/create", data={
            "token": token, "day": "2026-10-14",
            "activity_name": "Early breakfast",
            "planned_time": "06:30", "end_time": "06:50",
            "mode": "completed", "energy_before": "80", "energy_after": "70",
        }, follow_redirects=False)
        assert recorded.status_code == 303
        for activity, delta in (("Walk", "-25"), ("Appointment", "")):
            planned = client.post("/planner/calendar-event", data={
                "token": token, "day": "2026-10-14",
                "activity_name": activity, "planned_time": "10:00",
                "end_time": "11:00", "mode": "planned",
                "expected_delta": delta,
            }, follow_redirects=False)
            assert planned.status_code == 303

        # Thursday is overbooked; Monday has no saved morning score.
        client.post("/planner/energy", data={
            "token": token, "day": "2026-10-15",
            "starting_energy": "15", "view": "week",
        }, follow_redirects=False)
        client.post("/planner/calendar-event", data={
            "token": token, "day": "2026-10-15",
            "activity_name": "Cleaning", "planned_time": "13:00",
            "end_time": "14:00", "mode": "planned", "expected_delta": "-25",
        }, follow_redirects=False)

        printed = client.get("/planner/print?week=2026-10-14")
        assert printed.status_code == 200
        assert printed.text.count('class="print-energy-remaining') == 7
        # The print and screen use the same daily_energy_projection values.
        assert "≈45 left" in printed.text
        assert "≈-10 left" in printed.text
        assert "— left" in printed.text
        assert "print-energy-deficit" in printed.text
        assert 'class="print-title"' not in printed.text
        assert 'data-count="30"' in printed.text
        assert 'class="remaining-unknown"' not in printed.text
        assert "/static/print.css?v=0.2.11" in printed.text
        assert "/static/print.js?v=0.2.11" in printed.text
        screen = client.get("/planner/week?week=2026-10-14").text
        assert 'class="remaining-value">≈45</span>' in screen
    finally:
        client.__exit__(None, None, None)


def test_print_energy_summary_keeps_a4_full_bleed_dimensions():
    from pathlib import Path
    base = Path(__file__).resolve().parents[1] / "app" / "static"
    css = (base / "print.css").read_text()
    js = (base / "print.js").read_text()
    template = (
        Path(__file__).resolve().parents[1] / "app" / "templates"
        / "planner" / "print.html"
    ).read_text()
    assert "@page{size:A4 landscape;margin:0}" in css
    assert "height:10mm" in css
    assert "const rowMm = 200 / count;" in js
    assert 'class="print-energy-remaining' in template
    assert "d.projection.is_estimate" in template
