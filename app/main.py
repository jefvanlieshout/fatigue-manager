"""Fatigue Manager: private, minimal activity and energy diary."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from .i18n import language, locale_context, translate

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("FATIGUE_DB_PATH", "/var/lib/fatigue-manager/fatigue.sqlite3"))
TZ = ZoneInfo(os.getenv("FATIGUE_TIMEZONE", "Europe/Brussels"))
PASSWORD_HASH = os.getenv("FATIGUE_PASSWORD_HASH", "")
LOGIN_FAILURES: dict[str, list[float]] = {}
templates = Jinja2Templates(directory=str(APP_DIR / "templates"), context_processors=[locale_context])


def hash_password(password: str, salt: bytes | None = None) -> str:
    """scrypt hash in salt:hash hex format, with a per-password random salt."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str) -> bool:
    try:
        salt_hex, expected_hex = PASSWORD_HASH.split(":", 1)
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(expected_hex)
        if len(salt) != 16 or len(expected) != 64:
            return False
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 10000")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > 6:
            raise RuntimeError("Database schema is newer than this app; restore matching code.")
        if version == 0:
            db.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_name TEXT NOT NULL,
                    energy_before INTEGER NOT NULL CHECK(energy_before BETWEEN 0 AND 100),
                    energy_after INTEGER NOT NULL CHECK(energy_after BETWEEN 0 AND 100),
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_entries_occurred ON entries(occurred_at)")
            db.execute("PRAGMA user_version=1")


def csrf(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


def check_csrf(request: Request, token: str) -> None:
    stored = request.session.get("csrf", "")
    if not stored or not hmac.compare_digest(str(stored), str(token)):
        raise HTTPException(403, "Invalid form token. Refresh the page and try again.")


def logged_in(request: Request) -> bool:
    return request.session.get("authenticated") is True


def require_login(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    return None


def local_time(utc_text: str) -> datetime:
    return datetime.fromisoformat(utc_text).astimezone(TZ)


def date_bounds(day: date) -> tuple[str, str]:
    start = datetime.combine(day, datetime_time.min, tzinfo=TZ)
    end = datetime.combine(day + timedelta(days=1), datetime_time.min, tzinfo=TZ)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


def parsed_day(text: str | None) -> date:
    if not text:
        return datetime.now(TZ).date()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(400, "Invalid date") from exc


def parse_entry(name: str, before: int, after: int, occurred_at: str) -> tuple:
    name = " ".join(name.strip().split())
    if not 1 <= len(name) <= 120:
        raise HTTPException(422, "Activity name must be 1 to 120 characters.")
    if not (0 <= before <= 100 and 0 <= after <= 100):
        raise HTTPException(422, "Energy values must be between 0 and 100.")
    try:
        naive = datetime.strptime(occurred_at, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise HTTPException(422, "Invalid activity date/time.") from exc
    if not (2000 <= naive.year <= 2100):
        raise HTTPException(422, "Activity date/time out of range.")
    utc = naive.replace(tzinfo=TZ).astimezone(timezone.utc).isoformat()
    return name, before, after, utc


def activity_rows(day: date) -> list[dict]:
    start, end = date_bounds(day)
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM entries WHERE calendar_visible=0 AND occurred_at >= ? AND occurred_at < ? ORDER BY occurred_at DESC, id DESC",
            (start, end),
        ).fetchall()
    return [
        {
            **dict(row),
            "display_time": local_time(row["occurred_at"]).strftime("%H:%M"),
            "display_end": local_time(row["ended_at"]).strftime("%H:%M") if row["ended_at"] else None,
            "delta": row["energy_after"] - row["energy_before"],
        }
        for row in rows
    ]


def suggestions() -> list[str]:
    """Names used anywhere: recorded, one-off planned, or recurring.

    Recent first; a new activity only needs to be entered once.
    """
    with connect() as db:
        rows = db.execute("""
            SELECT activity_name, MAX(recent) AS recent FROM (
                SELECT activity_name, occurred_at AS recent FROM entries
                UNION ALL
                SELECT activity_name, created_at AS recent FROM planned_activities
                UNION ALL
                SELECT activity_name, created_at AS recent FROM recurring_rules
            ) GROUP BY activity_name COLLATE NOCASE
            ORDER BY recent DESC LIMIT 60
        """).fetchall()
    found, names = set(), []
    for row in rows:
        name = row["activity_name"].strip()
        if name and name.casefold() not in found:
            found.add(name.casefold())
            names.append(name)
    return names


def page_context(request: Request, day: date, editing: dict | None = None) -> dict:
    return {
        "request": request,
        "csrf": csrf(request),
        "day": day.isoformat(),
        "today": datetime.now(TZ).date().isoformat(),
        "previous": (day - timedelta(days=1)).isoformat(),
        "next": (day + timedelta(days=1)).isoformat(),
        "entries": activity_rows(day),
        "suggestions": suggestions(),
        "editing": editing,
        "default_time": (
            local_time(editing["occurred_at"]).strftime("%Y-%m-%dT%H:%M")
            if editing else datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
        ),
        "default_end": (
            local_time(editing["ended_at"]).strftime("%Y-%m-%dT%H:%M")
            if editing and editing["ended_at"] else ""
        ),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not PASSWORD_HASH:
        raise RuntimeError("FATIGUE_PASSWORD_HASH not configured. Run scripts/install.sh.")
    init_db()
    from .planner import initialize_planner_database
    initialize_planner_database()
    yield


app = FastAPI(title="Fatigue Manager", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("FATIGUE_SESSION_SECRET") or secrets.token_urlsafe(32),
    session_cookie="fatigue_session",
    same_site="lax",
    https_only=os.getenv("FATIGUE_COOKIE_SECURE", "0") == "1",
    max_age=60 * 60 * 24 * 30,
)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.middleware("http")
async def safety_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if logged_in(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html", context={"csrf": csrf(request), "error": ""}
    )


@app.post("/login")
def login(request: Request, password: str = Form(...), token: str = Form(...)):
    check_csrf(request, token)
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    failures = [t for t in LOGIN_FAILURES.get(ip, []) if now - t < 300]
    if len(failures) >= 8:
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")
    if verify_password(password):
        LOGIN_FAILURES.pop(ip, None)
        request.session.clear()
        request.session["authenticated"] = True
        csrf(request)
        return RedirectResponse("/", status_code=303)
    failures.append(now)
    LOGIN_FAILURES[ip] = failures
    return templates.TemplateResponse(
        request=request, name="login.html", context={"csrf": csrf(request), "error": translate(language(request), "wrong_password")},
        status_code=401,
    )


@app.post("/logout")
def logout(request: Request, token: str = Form(...)):
    check_csrf(request, token)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, day: str | None = None):
    if redirect := require_login(request):
        return redirect
    return templates.TemplateResponse(
        request=request, name="index.html", context=page_context(request, parsed_day(day))
    )


@app.post("/entries")
def add_entry(
    request: Request,
    activity_name: str = Form(...),
    energy_before: int = Form(...),
    energy_after: int = Form(...),
    occurred_at: str = Form(...),
    ended_at: str = Form(""),
    token: str = Form(...),
):
    if redirect := require_login(request):
        return redirect
    check_csrf(request, token)
    name, before, after, occurred = parse_entry(activity_name, energy_before, energy_after, occurred_at)
    from .planner import actual_end
    ending = actual_end(occurred, ended_at)
    with connect() as db:
        db.execute(
            "INSERT INTO entries(activity_name,energy_before,energy_after,occurred_at,created_at,ended_at,calendar_visible) "
            "VALUES(?,?,?,?,?,?,0)",
            (name, before, after, occurred, datetime.now(timezone.utc).isoformat(), ending),
        )
    day = local_time(occurred).date().isoformat()
    return RedirectResponse("/?day=" + day, status_code=303)


def find_entry(entry_id: int) -> dict:
    with connect() as db:
        row = db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Activity not found.")
    return dict(row)


@app.get("/entries/{entry_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, entry_id: int):
    if redirect := require_login(request):
        return redirect
    entry = find_entry(entry_id)
    return templates.TemplateResponse(
        request=request, name="index.html",
        context=page_context(request, local_time(entry["occurred_at"]).date(), editing=entry)
    )


@app.post("/entries/{entry_id}/edit")
def save_edit(
    request: Request,
    entry_id: int,
    activity_name: str = Form(...),
    energy_before: int = Form(...),
    energy_after: int = Form(...),
    occurred_at: str = Form(...),
    ended_at: str = Form(""),
    token: str = Form(...),
):
    if redirect := require_login(request):
        return redirect
    check_csrf(request, token)
    find_entry(entry_id)
    name, before, after, occurred = parse_entry(activity_name, energy_before, energy_after, occurred_at)
    from .planner import actual_end
    ending = actual_end(occurred, ended_at)
    with connect() as db:
        db.execute(
            "UPDATE entries SET activity_name=?,energy_before=?,energy_after=?,occurred_at=?,ended_at=? WHERE id=?",
            (name, before, after, occurred, ending, entry_id)
        )
    return RedirectResponse("/?day=" + local_time(occurred).date().isoformat(), status_code=303)


@app.post("/entries/{entry_id}/delete")
def delete_entry(request: Request, entry_id: int, token: str = Form(...)):
    if redirect := require_login(request):
        return redirect
    check_csrf(request, token)
    entry = find_entry(entry_id)
    with connect() as db:
        db.execute("UPDATE planned_activities SET status='planned', linked_entry_id=NULL WHERE linked_entry_id=?", (entry_id,))
        db.execute("DELETE FROM recurring_exceptions WHERE linked_entry_id=?", (entry_id,))
        db.execute("DELETE FROM entries WHERE id=?", (entry_id,))
    return RedirectResponse(
        "/?day=" + local_time(entry["occurred_at"]).date().isoformat(), status_code=303
    )


@app.get("/export.csv")
def export_csv(request: Request):
    if redirect := require_login(request):
        return redirect
    with connect() as db:
        entries = db.execute("SELECT * FROM entries ORDER BY occurred_at, id").fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "activity", "energy_before", "energy_after", "change", "local_datetime", "utc_datetime"])
    for row in entries:
        name = row["activity_name"]
        # Avoid spreadsheet formula execution when opening exported CSV files.
        if name and name[0] in "=+-@\t\r\n":
            name = "'" + name
        writer.writerow([
            row["id"], name, row["energy_before"], row["energy_after"],
            row["energy_after"] - row["energy_before"],
            local_time(row["occurred_at"]).isoformat(), row["occurred_at"],
        ])
    return Response(
        "\ufeff" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="fatigue-activities.csv"'},
    )

@app.post("/language")
def choose_language(
    request: Request, lang: str = Form(...), return_to: str = Form("/"),
    token: str = Form(...),
):
    check_csrf(request, token)
    if lang not in ("en", "nl"):
        raise HTTPException(422, "Unsupported language.")
    if not return_to.startswith("/") or return_to.startswith("//") or chr(92) in return_to or any(ord(c) < 32 for c in return_to):
        return_to = "/"
    response = RedirectResponse(return_to, status_code=303)
    response.set_cookie(
        "fatigue_locale", lang, max_age=365 * 86400, httponly=True,
        secure=os.getenv("FATIGUE_COOKIE_SECURE", "0") == "1", samesite="lax"
    )
    return response


from .planner import router as planner_router
app.include_router(planner_router)
