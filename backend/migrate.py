"""Simple SQLite migration helper for the AWS Agent backend.

Run this script before starting the backend to ensure the database and
required tables exist.

Usage:
    python3 backend/migrate.py
"""

from app.db import Base, DATA_DIR, DB_PATH, engine


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"SQLite schema created or verified at: {DB_PATH}")


if __name__ == "__main__":
    main()
