from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import sqlite3

DATABASE_URL = "sqlite:///./tender_eval.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def _migrate():
    """Add new columns to existing tables without dropping data."""
    conn = sqlite3.connect("./tender_eval.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenderanalysis'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(tenderanalysis)")
        existing = {row[1] for row in cur.fetchall()}
        for col, typ in [("overview_json", "TEXT"), ("items_json", "TEXT")]:
            if col not in existing:
                cur.execute(f"ALTER TABLE tenderanalysis ADD COLUMN {col} {typ}")
    conn.commit()
    conn.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
