from collections.abc import Generator
from pathlib import Path
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_database_url(raw_url: str) -> str:
    url = make_url(raw_url)
    if url.get_backend_name() != "sqlite":
        return raw_url

    if url.database in (None, "", ":memory:"):
        return raw_url

    db_path = Path(url.database)
    if not db_path.is_absolute():
        db_path = (PROJECT_ROOT / db_path).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        db_path.touch(exist_ok=True)
    except PermissionError as exc:
        raise RuntimeError(f"SQLite database is not writable: {db_path}") from exc

    if not os.access(db_path, os.W_OK):
        raise RuntimeError(f"SQLite database is not writable: {db_path}")

    return str(url.set(database=str(db_path)))


class Base(DeclarativeBase):
    pass


resolved_database_url = _resolve_database_url(settings.database_url)
connect_args = {"check_same_thread": False, "timeout": 30} if resolved_database_url.startswith("sqlite") else {}
engine = create_engine(resolved_database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
