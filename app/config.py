from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR / 'app.db'}"
UPLOAD_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
WORKITEM_TEMPLATES_DIR = BASE_DIR / "app" / "modules" / "workitems" / "templates"
