from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings

# Normalize SQLite relative path to backend directory to avoid multiple DB files
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    path = db_url[len("sqlite:///") :]
    # If path is relative (does not start with '/'), anchor it to backend directory
    if path and not path.startswith("/"):
        backend_dir = Path(__file__).resolve().parents[2]  # backend/
        abs_path = (backend_dir / path).resolve()
        db_url = f"sqlite:///{abs_path}"

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
