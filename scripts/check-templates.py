"""Preflight: compile every Jinja template before deploying a release."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

root = Path(__file__).resolve().parents[1] / "app" / "templates"
env = Environment(loader=FileSystemLoader(str(root)), autoescape=True)
names = env.list_templates(extensions=["html"])
if not names:
    raise SystemExit("No HTML templates found")
for name in names:
    env.get_template(name)
    print("OK:", name)
print(f"Template preflight passed: {len(names)} templates")
