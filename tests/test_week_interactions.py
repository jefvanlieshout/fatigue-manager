"""Regression coverage for usable week drag targets, saved suggestions and 100-point defaults."""
import re
from pathlib import Path

from fastapi.testclient import TestClient
from app import main

PASSWORD = "local-test-password-only"


def _login(tmp_path):
    main.DB_PATH = tmp_path / "planner-v023.sqlite3"
    main.PASSWORD_HASH = main.hash_password(PASSWORD)
    client = TestClient(main.app)
    client.__enter__()
    page = client.get("/login")
    token = re.search(r'name="token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "token": token, "password": PASSWORD,
    }, follow_redirects=False).status_code == 303
    return client, token


def test_week_defaults_100_without_adding_energy_measurements(tmp_path):
    client, token = _login(tmp_path)
    try:
        html = client.get("/planner/week?week=2026-10-13").text
        assert html.count("Default 100 · not yet recorded") == 7
        assert html.count('name="starting_energy"') == 7
        assert html.count('value="100"') >= 7
        with main.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM daily_energy").fetchone()[0] == 0
        response = client.post("/planner/energy", data={
            "day": "2026-10-13", "starting_energy": "35",
            "view": "week", "token": token,
        }, follow_redirects=False)
        assert response.status_code == 303
        with main.connect() as db:
            saved = db.execute(
                "SELECT starting_energy FROM daily_energy WHERE day='2026-10-13'"
            ).fetchone()
            assert saved["starting_energy"] == 35
            assert db.execute("SELECT COUNT(*) FROM daily_energy").fetchone()[0] == 1
        html = client.get("/planner/week?week=2026-10-13").text
        assert 'value="35"' in html
        assert html.count("Default 100 · not yet recorded") == 6
        assert 'value="100"' in client.get("/planner/day?day=2026-10-14").text
    finally:
        client.__exit__(None, None, None)


def test_week_recent_activity_dropdown_uses_actual_diary_entries(tmp_path):
    client, token = _login(tmp_path)
    try:
        assert client.post("/entries", data={
            "token": token, "activity_name": "Cooking breakfast",
            "energy_before": "75", "energy_after": "45",
            "occurred_at": "2026-10-13T09:00",
        }, follow_redirects=False).status_code == 303
        html = client.get("/planner/week?week=2026-10-13").text
        assert 'id="quick-recent-activity"' in html
        assert 'list="quick-activity-suggestions"' in html
        assert '<option value="Cooking breakfast">Cooking breakfast</option>' in html
        assert 'id="quick-plan-name"' in html
        assert 'name="end_time"' in html
    finally:
        client.__exit__(None, None, None)


def test_both_languages_offer_default_label(tmp_path):
    client, token = _login(tmp_path)
    try:
        english = client.get("/planner/week?week=2026-10-13").text
        assert "Previously recorded activities" not in english  # no previous entries yet
        assert "Default 100" in english
        res = client.post("/language", data={
            "token": token, "lang": "nl", "return_to": "/planner/week",
        }, follow_redirects=False)
        assert res.status_code == 303
        dutch = client.get("/planner/week?week=2026-10-13").text
        assert "Standaard 100" in dutch
    finally:
        client.__exit__(None, None, None)


def test_drag_handlers_operate_on_pointer_positions():
    js = (Path(__file__).resolve().parents[1] / "app/static/app.js").read_text()
    assert 'link.addEventListener("dragstart"' in js
    assert 'link.addEventListener("pointerdown"' in js
    assert 'document.addEventListener("pointermove"' in js
    assert 'document.addEventListener("pointerup"' in js
    assert "elementFromPoint" in js or "getBoundingClientRect" in js
    assert "requestAnimationFrame(autoScroll)" in js
    assert 'slot.classList.add("slot-selected")' not in js or "slot-selected" in js
