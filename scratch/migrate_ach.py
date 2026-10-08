# scratch/migrate_ach.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Check dialect
        dialect_name = engine.dialect.name
        print(f"Connected to dialect: {dialect_name}")

        columns_to_add = [
            ("evidence_assessments", "original_classification", "VARCHAR"),
            ("evidence_assessments", "analyst_override", "BOOLEAN DEFAULT FALSE"),
            ("evidence_assessments", "analyst_notes", "TEXT"),
            ("hypotheses", "disconfirmation_penalty", "FLOAT DEFAULT 0.0"),
        ]

        for table, col, col_type in columns_to_add:
            try:
                if dialect_name == "postgresql":
                    stmt = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type};"
                else: # sqlite
                    stmt = f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"
                conn.execute(text(stmt))
                conn.commit()
                print(f"[OK] Added column {col} to {table}")
            except Exception as e:
                print(f"[-] Column {col} on {table}: {e}")

if __name__ == "__main__":
    migrate()
