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

if raw_url:
    db_url = raw_url.strip()
    # Ensure SSL mode for Supabase / remote PostgreSQL
    if db_url.startswith("postgresql://") or db_url.startswith("postgresql+psycopg://"):
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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
