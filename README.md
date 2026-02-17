# ESOP Management Tool

Production-ready ESOP management web app for internal company use, built with **FastAPI + SQLite**.

## What it supports

- Employee management (create, list, update, deactivate)
- Grant management (create, list, update)
- Vesting computation with cliff + periodic vesting
- Exercise recording with validation against vested quantity
- Dashboard metrics for pool allocation and vesting status
- Browser UI at `/` and API docs at `/docs`

## Tech stack

- FastAPI (API + web serving)
- SQLAlchemy 2.0 ORM
- SQLite database
- Vanilla JS frontend
- Pytest test suite

## Quick start (local)

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Configure environment:

```bash
cp .env.example .env
```

3. Run the server:

```bash
uvicorn app.main:app --reload
```

4. Open:

- UI: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs

Database file (`esop.db`) is created automatically on startup.

If you run the app from another working directory, the SQLite path is still resolved against this project root to avoid read-only DB path issues.

## Run tests

```bash
pytest
```

## API overview

- `GET /health`
- `POST /api/employees`
- `GET /api/employees`
- `PATCH /api/employees/{employee_id}`
- `DELETE /api/employees/{employee_id}`
- `POST /api/grants`
- `GET /api/grants`
- `PATCH /api/grants/{grant_id}`
- `POST /api/grants/{grant_id}/exercises`
- `GET /api/grants/{grant_id}/summary`
- `GET /api/dashboard/summary`

## Production notes

- Set `ENVIRONMENT=production` and `DEBUG=false`.
- Restrict CORS with `CORS_ORIGINS` (comma-separated origins).
- Use regular DB backups of `esop.db`.
- Run behind a reverse proxy/load balancer in production.

## Troubleshooting

- `sqlite3.OperationalError: attempt to write a readonly database`
  - Ensure the process user has write permission to this project folder (or set `DATABASE_URL` to an absolute writable path like `sqlite:////tmp/esop.db`).

## Docker

Build and run:

```bash
docker build -t esop-tool .
docker run --rm -p 8000:8000 -v "$(pwd)":/app esop-tool
```
