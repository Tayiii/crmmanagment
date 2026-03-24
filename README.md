# WorkItems MVP

MVP внутренней системы менеджмента поручений и запросов для предприятия на FastAPI + async SQLAlchemy + SQLite + Jinja2.

## Архитектура

- `app/core`: базовые сущности пользователей, ролей, подразделений, файлов и простая demo-auth заготовка.
- `app/modules/workitems`: изолированный модуль WorkItem со своими моделями, сервисом, роутами и шаблонами.
- одна SQLite БД (`app.db`).

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

После старта приложение создаёт БД и demo-пользователей.
