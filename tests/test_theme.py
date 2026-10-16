"""Manual light/dark theme controls; no automatic switching or print changes."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.i18n import LANGUAGES

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "test-manual-theme-123"


def test_theme_toggle_visible_on_login_and_week_planner(tmp_path):
    main.DB_PATH = tmp_path / "theme.sqlite3"
    main.PASSWORD_HASH = main.hash_password(PASSWORD)
    with TestClient(main.app) as client:
        login = client.get("/login")
        assert login.status_code == 200
        assert 'id="theme-toggle"' in login.text
        assert 'aria-pressed="false"' in login.text
        assert 'class="theme-icon-moon"' in login.text
        assert 'class="theme-icon-sun"' in login.text
        assert 'data-dark-label="Switch to dark mode"' in login.text
        assert 'data-light-label="Switch to light mode"' in login.text

        # Non-deferred theme bootstrap precedes the CSS to prevent light flash.
        assert login.text.index('/static/theme.js?v=0.2.13') < login.text.index(
            '/static/style.css?v=0.2.13'
        )
        assert '/static/app.js?v=0.2.13' in login.text
        assert client.get("/static/theme.js").status_code == 200

        token = re.search(r'name="token" value="([^"]+)"', login.text).group(1)
        assert client.post("/login", data={
            "token": token, "password": PASSWORD,
        }, follow_redirects=False).status_code == 303
        for route in ("/", "/planner/week?week=2026-10-14",
                      "/planner/day?day=2026-10-14",
                      "/planner/settings?week=2026-10-14"):
            response = client.get(route)
            assert response.status_code == 200
            assert 'id="theme-toggle"' in response.text


def test_theme_is_manual_and_stored_only_in_browser():
    script = (ROOT / "app/static/theme.js").read_text()
    base = (ROOT / "app/templates/base.html").read_text()
    style = (ROOT / "app/static/style.css").read_text()
    assert 'const STORAGE_KEY = "fatigue-manager-theme"' in script
    assert 'localStorage.getItem(STORAGE_KEY)' in script
    assert 'localStorage.setItem(STORAGE_KEY, next)' in script
    assert 'toggle.addEventListener("click"' in script
    assert 'window.addEventListener("storage"' in script
    assert 'toggle.setAttribute("aria-pressed", String(dark))' in script
    assert 'toggle.setAttribute("aria-label", nextLabel)' in script
    assert 'theme === "dark"' in script
    # Theme is NEVER tied to the clock or to system/browser appearance.
    assert 'prefers-color-scheme' not in script
    assert "matchMedia(" not in script
    assert "setInterval(" not in script
    assert "new Date(" not in script
    assert "prefers-color-scheme" not in base
    assert 'html[data-theme="dark"]' in style
    assert 'html[data-theme="dark"] .calendar-scroll' in style
    assert 'html[data-theme="dark"] .calendar-dialog' in style
    assert 'html[data-theme="dark"] .calendar-dialog .activity-suggest-panel' in style
    assert 'html[data-theme="dark"] .calendar-day-head.calendar-today' in style
    assert 'html[data-theme="dark"] .calendar-energy-inline input[type="number"]' in style
    assert '.theme-icon-sun{display:none}' in style


def test_print_page_remains_on_independent_light_stylesheet():
    print_page = (ROOT / "app/templates/planner/print.html").read_text()
    css = (ROOT / "app/static/print.css").read_text()
    assert 'href="/static/print.css?v=0.2.12"' in print_page
    assert '/static/theme.js' not in print_page
    assert '/static/style.css' not in print_page
    assert 'color:#173427' in css
    assert '@page{size:A4 landscape;margin:0}' in css


def test_theme_labels_have_english_and_dutch_translations():
    for lang in ("en", "nl"):
        assert LANGUAGES[lang]["enable_dark_mode"]
        assert LANGUAGES[lang]["enable_light_mode"]
    assert set(LANGUAGES["en"]) == set(LANGUAGES["nl"])
