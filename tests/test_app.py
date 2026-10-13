import os
import re
os.environ["FATIGUE_DB_PATH"]="/tmp/fatigue-tests-dummy.sqlite3"
os.environ["FATIGUE_SESSION_SECRET"]="test-only-secret"
os.environ["FATIGUE_PASSWORD_HASH"]="test"
from fastapi.testclient import TestClient
from app import main

def test_login_crud_and_export(tmp_path):
    main.DB_PATH=tmp_path/"test.sqlite3"
    main.PASSWORD_HASH=main.hash_password("test-password-123")
    with TestClient(main.app) as client:
        assert client.get("/").status_code==200  # follows login redirect
        page=client.get("/login")
        csrf=re.search(r'name="token" value="([^"]+)"',page.text).group(1)
        assert client.post("/login",data={"password":"test-password-123","token":csrf}).status_code==200
        page=client.get("/")
        csrf=re.search(r'name="token" value="([^"]+)"',page.text).group(1)
        payload={"activity_name":"Koken","energy_before":"75","energy_after":"45","occurred_at":"2026-10-13T11:30","token":csrf}
        assert client.post("/entries",data=payload,follow_redirects=False).status_code==303
        assert "Koken" in client.get("/?day=2026-10-13").text
        assert "-30" in client.get("/export.csv").text
        with main.connect() as db:
            entry=db.execute("SELECT id FROM entries").fetchone()[0]
        payload["activity_name"]="Wandelen"
        assert client.post(f"/entries/{entry}/edit",data=payload,follow_redirects=False).status_code==303
        assert "Wandelen" in client.get("/?day=2026-10-13").text
        assert client.post(f"/entries/{entry}/delete",data={"token":csrf},follow_redirects=False).status_code==303
        assert "Wandelen" not in client.get("/?day=2026-10-13").text

def test_password_and_input_validation():
    main.PASSWORD_HASH=main.hash_password("correct password")
    assert main.verify_password("correct password")
    assert not main.verify_password("wrong")
    try:
        main.parse_entry("test",101,10,"2026-10-13T11:30")
        assert False
    except Exception as e:
        assert e.status_code==422

def test_dst_day():
    from datetime import date,datetime
    a,b=main.date_bounds(date(2026,3,29))
    assert (datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds()==23*3600

def test_all_html_templates_compile():
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app" / "templates"
    env = Environment(loader=FileSystemLoader(str(root)), autoescape=True)
    for name in env.list_templates(extensions=["html"]):
        env.get_template(name)
