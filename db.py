"""
Database abstraction: SQLite (local dev) or PostgreSQL (production).
Set DATABASE_URL env var → auto-switch to PostgreSQL. Otherwise SQLite.
"""
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_PG = bool(DATABASE_URL)

# Fix Render's postgres:// → postgresql:// (psycopg2 requirement)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    os.environ["DATABASE_URL"] = DATABASE_URL

if IS_PG:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    IntegrityError = psycopg2.IntegrityError
else:
    import sqlite3
    IntegrityError = sqlite3.IntegrityError


def connect():
    """Create a new database connection."""
    if IS_PG:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        conn.autocommit = False
        return conn
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "absensi.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def run(db, sql, params=()):
    """Execute SQL with auto placeholder conversion (? → %s for PG). Returns cursor."""
    cur = db.cursor()
    cur.execute(adapt(sql), params)
    return cur


def fetchone(cur):
    """Fetch one row as dict."""
    row = cur.fetchone()
    return dict(row) if row else None


def fetchall(cur):
    """Fetch all rows as list of dicts."""
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def insert_returning(db, sql, params=()):
    """Execute INSERT and return the new row's id."""
    if IS_PG:
        # Append RETURNING id if not already present
        s = sql.rstrip().rstrip(";")
        s += " RETURNING id"
        cur = db.cursor()
        cur.execute(adapt(s), params)
        row = cur.fetchone()
        return row["id"] if row else None
    else:
        cur = db.cursor()
        cur.execute(sql, params)
        return cur.lastrowid


def adapt(sql):
    """Convert SQLite ? placeholders to PostgreSQL %s."""
    if IS_PG:
        return sql.replace("?", "%s")
    return sql
