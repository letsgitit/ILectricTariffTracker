import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("TARIFF_DB_PATH", "/data/tariff_tracker.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    from app.models import Base
    Base.metadata.create_all(bind=engine)
