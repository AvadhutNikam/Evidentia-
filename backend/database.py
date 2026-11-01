# backend/database.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Reliably load .env from the backend directory regardless of working directory
BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

raw_url = os.getenv("DATABASE_URL")
engine = None

if raw_url and (raw_url.startswith("postgresql://") or raw_url.startswith("postgresql+psycopg://")):
    db_url = raw_url.strip()
    if "sslmode" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url += f"{separator}sslmode=require"
    try:
        test_engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        with test_engine.connect() as conn:
            pass
        engine = test_engine
        print("[OK] Connected to remote PostgreSQL / Supabase database.")
    except Exception as e:
        print(f"[!] Remote PostgreSQL connection failed: {e}")
        print("[!] Falling back to local SQLite database (evidentia.db).")
        engine = None

if engine is None:
    # Use absolute path to evidentia.db so cases are always loaded correctly
    sqlite_db_path = (BACKEND_DIR / "evidentia.db").resolve()
    # On Windows SQLite URL format: sqlite:///<path>
    db_url = f"sqlite:///{sqlite_db_path.as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    print(f"[OK] Using local SQLite database: {sqlite_db_path}")

from sqlalchemy import event

if "sqlite" in db_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_database_schema(target_engine=None):
    """Ensures optional columns exist in tables without breaking existing SQLite/PostgreSQL schemas."""
    from sqlalchemy import text
    eng = target_engine or engine
    if eng is None:
        return
    with eng.connect() as conn:
        if "sqlite" in str(eng.url):
            try:
                res = conn.execute(text("PRAGMA integrity_check")).fetchone()
                print(f"[OK] SQLite database integrity check: {res[0] if res else 'ok'}")
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()
            except Exception as e:
                print(f"[!] SQLite PRAGMA check: {e}")
        for stmt in [
            "ALTER TABLE cases ADD COLUMN is_demo BOOLEAN DEFAULT 0",
            "ALTER TABLE evidence ADD COLUMN extraction_mode VARCHAR DEFAULT 'live'",
            "ALTER TABLE evidence ADD COLUMN is_demo_fixture BOOLEAN DEFAULT 0",
            "ALTER TABLE events ADD COLUMN latitude FLOAT",
            "ALTER TABLE events ADD COLUMN longitude FLOAT",
            "ALTER TABLE events ADD COLUMN event_type VARCHAR(64)",
            "ALTER TABLE events ADD COLUMN time_uncertainty_minutes INTEGER DEFAULT 0",
            """CREATE TABLE IF NOT EXISTS watchlist_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_by_name VARCHAR(128),
                case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
                entity_type VARCHAR(32) NOT NULL,
                entity_value VARCHAR(255) NOT NULL,
                label VARCHAR(255) NOT NULL,
                priority VARCHAR(32) NOT NULL DEFAULT 'critical',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                notes TEXT,
                match_count INTEGER NOT NULL DEFAULT 0,
                last_matched_at TIMESTAMP,
                last_matched_case_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )""",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass

ensure_database_schema(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
