from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _create_engine():
    settings = get_settings()
    url = settings.effective_database_url
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "", 1)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    from app.repositories import orm_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_compat_migrations()


def get_db() -> Generator[Session]:
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> bool:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _apply_sqlite_compat_migrations() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "tickets" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tickets")}
    migrations = {
        "category": "ALTER TABLE tickets ADD COLUMN category TEXT",
        "priority": "ALTER TABLE tickets ADD COLUMN priority TEXT",
        "escalation_required": "ALTER TABLE tickets ADD COLUMN escalation_required BOOLEAN NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))
