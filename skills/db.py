"""Tiny DB helper: PostgreSQL in production, SQLite fallback for local dev/tests."""
import os
import sqlite3
import time

URL = os.environ.get("DATABASE_URL", "sqlite:///skills_local.db")
PG = URL.startswith("postgres")
PK = "SERIAL PRIMARY KEY" if PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _connect():
    if PG:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(URL, cursor_factory=RealDictCursor)
    c = sqlite3.connect(URL.replace("sqlite:///", ""), timeout=10)
    c.row_factory = sqlite3.Row
    return c


def run(sql, args=(), fetch=None):
    """fetch: None | 'one' | 'all'. Returns (result, rowcount)."""
    if not PG:
        sql = sql.replace("%s", "?")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        out = None
        if fetch == "one":
            r = cur.fetchone()
            out = dict(r) if r else None
        elif fetch == "all":
            out = [dict(r) for r in cur.fetchall()]
        conn.commit()
        return out, cur.rowcount
    finally:
        conn.close()


def wait_for_db(retries=30):
    for i in range(retries):
        try:
            _connect().close()
            return
        except Exception as e:  # DB pod may still be starting
            print(f"waiting for database ({e})", flush=True)
            time.sleep(2)
    raise RuntimeError("database unreachable")
