"""生产/预发入口：``gunicorn -w 4 -k gthread --threads 2 backend.wsgi:app``。"""
from __future__ import annotations

from backend import create_app
from backend.services.jobs import start_scheduler

app = create_app()
start_scheduler(app)

__all__ = ["app"]
