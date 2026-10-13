"""Calendar presentation preferences. No user health records here."""
import re
from fastapi import HTTPException
from .main import connect

DEFAULTS = dict(low_max=10, medium_max=20, low_color="#4eaa79",
    medium_color="#eba34a", high_color="#db5e68",
    day_start=6, day_end=23, print_start=7, print_end=22)

def init_preferences():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (4, 5):
            raise RuntimeError("Expected v4 or v5 database")
        db.execute("""CREATE TABLE IF NOT EXISTS app_preferences (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            low_max INTEGER NOT NULL, medium_max INTEGER NOT NULL,
            low_color TEXT NOT NULL, medium_color TEXT NOT NULL, high_color TEXT NOT NULL,
            day_start INTEGER NOT NULL, day_end INTEGER NOT NULL,
            print_start INTEGER NOT NULL, print_end INTEGER NOT NULL
        )""")
        db.execute("""INSERT OR IGNORE INTO app_preferences
            (id,low_max,medium_max,low_color,medium_color,high_color,
            day_start,day_end,print_start,print_end)
            VALUES (1,?,?,?,?,?,?,?,?,?)""", tuple(DEFAULTS.values()))
        db.execute("PRAGMA user_version=5")

def load_preferences():
    with connect() as db:
        row = db.execute("SELECT * FROM app_preferences WHERE id=1").fetchone()
    return dict(row) if row else {"id": 1, **DEFAULTS}

def validate_preferences(values):
    result = {}
    try:
        for key in ("low_max","medium_max","day_start","day_end","print_start","print_end"):
            result[key] = int(values[key])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "Invalid numeric setting") from exc
    if not (0 <= result["low_max"] < result["medium_max"] <= 100):
        raise HTTPException(422, "Energy ranges must increase.")
    for start, end in (("day_start","day_end"),("print_start","print_end")):
        if not (0 <= result[start] < result[end] <= 24):
            raise HTTPException(422, "Invalid time range")
    for key in ("low_color","medium_color","high_color"):
        value = str(values.get(key, ""))
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise HTTPException(422, "Invalid hex color")
        result[key] = value.lower()
    return result

def save_preferences(values):
    v = validate_preferences(values)
    with connect() as db:
        db.execute("""UPDATE app_preferences SET
            low_max=?,medium_max=?,day_start=?,day_end=?,print_start=?,print_end=?,
            low_color=?,medium_color=?,high_color=? WHERE id=1""",
            (v["low_max"],v["medium_max"],v["day_start"],v["day_end"],
            v["print_start"],v["print_end"],v["low_color"],v["medium_color"],v["high_color"]))

def energy_class(delta, prefs):
    if delta is None: return "energy-unknown"
    if delta > 0: return "energy-restored"
    if -delta <= prefs["low_max"]: return "energy-low"
    if -delta <= prefs["medium_max"]: return "energy-medium"
    return "energy-high"
