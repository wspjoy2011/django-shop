from pathlib import Path
import sys
import os

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("USE_PGBOUNCER", "false")
os.environ.setdefault("POSTGRES_USER", "mypy")
os.environ.setdefault("POSTGRES_PASSWORD", "mypy")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "mypy")

os.environ.setdefault("DATASETS_DIR", "/tmp")

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("GOOGLE_PLACES_API_KEY", "")

from .dev import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEBUG = False
