"""Gunicorn configuration (used by `gunicorn config.wsgi`)."""

import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 3)))
timeout = 30
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = "*"
