from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import sqlite3

DATABASE_URL = "sqlite:///./tender_eval.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def _migrate():
    """Add new columns to existing tables without dropping data."""
    conn = sqlite3.connect("./tender_eval.db")
    cur = conn.cursor()

    # tenderanalysis columns
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenderanalysis'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(tenderanalysis)")
        existing = {row[1] for row in cur.fetchall()}
        for col, typ in [("overview_json", "TEXT"), ("items_json", "TEXT")]:
            if col not in existing:
                cur.execute(f"ALTER TABLE tenderanalysis ADD COLUMN {col} {typ}")

    # criterion provenance columns
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='criterion'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(criterion)")
        existing = {row[1] for row in cur.fetchall()}
        for col, typ in [("source_page", "INTEGER"), ("source_bbox_json", "TEXT")]:
            if col not in existing:
                cur.execute(f"ALTER TABLE criterion ADD COLUMN {col} {typ}")

    # tender page_count
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tender'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(tender)")
        existing = {row[1] for row in cur.fetchall()}
        if "page_count" not in existing:
            cur.execute("ALTER TABLE tender ADD COLUMN page_count INTEGER DEFAULT 0")

    # bidder risk_score
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bidder'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(bidder)")
        existing = {row[1] for row in cur.fetchall()}
        if "risk_score" not in existing:
            cur.execute("ALTER TABLE bidder ADD COLUMN risk_score INTEGER DEFAULT NULL")

    conn.commit()
    conn.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
