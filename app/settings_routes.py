"""Settings and full-bleed A4 weekly calendar print view."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from .main import check_csrf, require_login, csrf, templates, parsed_day
from .preferences import load_preferences, save_preferences, energy_class
from .planner import week_data, calendar_week

router = APIRouter()

@router.post("/settings")
def update_settings(request: Request, token: str = Form(...), week: str = Form(...),
                    low_max: int = Form(...), medium_max: int = Form(...),
                    low_color: str = Form(...), medium_color: str = Form(...),
                    high_color: str = Form(...), day_start: int = Form(...),
                    day_end: int = Form(...), print_start: int = Form(...),
                    print_end: int = Form(...)):
    if response := require_login(request):
        return response
    check_csrf(request, token)
    selected = parsed_day(week)
    save_preferences(dict(low_max=low_max, medium_max=medium_max,
        low_color=low_color, medium_color=medium_color, high_color=high_color,
        day_start=day_start, day_end=day_end,
        print_start=print_start, print_end=print_end))
    return RedirectResponse("/planner/week?week=" + selected.isoformat(), status_code=303)

@router.get("/print")
def print_week(request: Request, week: str | None = None):
    if response := require_login(request):
        return response
    prefs = load_preferences()
    monday, days = week_data(parsed_day(week))
    slots, days = calendar_week(days, prefs["print_start"], prefs["print_end"])
    for day in days:
        for events in day["slots"].values():
            for event in events:
                event["energy_class"] = energy_class(event["delta"], prefs)
                event["estimated"] = event["kind"] == "planned"
    return templates.TemplateResponse(
        request=request, name="planner/print.html",
        context={"csrf": csrf(request), "monday": monday.isoformat(),
                 "days": days, "slots": slots, "prefs": prefs},
    )
