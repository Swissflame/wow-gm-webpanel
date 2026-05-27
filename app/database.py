from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .settings import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().panel_db_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Path("instance").mkdir(exist_ok=True)
    from . import models  # noqa
    Base.metadata.create_all(bind=engine)
