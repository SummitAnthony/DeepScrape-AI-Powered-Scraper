"""Scrape-history log: records every scraping job in SQLite for a dashboard view."""
import sqlite3
import time

DB_PATH = "scrape_history.db"


class HistoryStore:
    """SQLite log of scraping jobs."""

    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS jobs "
            "(id INTEGER PRIMARY KEY, url TEXT, mode TEXT, items_found INTEGER, logged_at REAL)"
        )
        self.conn.commit()

    def log_job(self, url, mode, items_found, logged_at=None):
        self.conn.execute(
            "INSERT INTO jobs (url, mode, items_found, logged_at) VALUES (?, ?, ?, ?)",
            (url, mode, items_found, logged_at if logged_at is not None else time.time()),
        )
        self.conn.commit()

    def list_jobs(self, limit=50):
        rows = self.conn.execute(
            "SELECT url, mode, items_found, logged_at FROM jobs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"url": u, "mode": m, "items_found": n, "logged_at": t} for u, m, n, t in rows]

    def close(self):
        self.conn.close()


def log_job(url, mode, items_found, db_path=DB_PATH):
    """Module-level convenience: log one job and close."""
    store = HistoryStore(db_path)
    try:
        store.log_job(url, mode, items_found)
    finally:
        store.close()


def list_jobs(limit=50, db_path=DB_PATH):
    """Module-level convenience: list jobs and close."""
    store = HistoryStore(db_path)
    try:
        return store.list_jobs(limit)
    finally:
        store.close()
