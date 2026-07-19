"""Watch mode: snapshot a page's text content and diff it between checks."""
import difflib
import sqlite3
import time

from bs4 import BeautifulSoup

DB_PATH = "watch_history.db"


def normalize_content(html):
    """Reduce HTML to comparable plain text: no scripts/styles, no blank lines."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style"]):
        tag.extract()
    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
    return "\n".join(line for line in lines if line)


def diff_texts(old, new):
    """Line diff between two texts. Returns {'added': [...], 'removed': [...]}."""
    added, removed = [], []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ "):
            added.append(line[2:])
        elif line.startswith("- "):
            removed.append(line[2:])
    return {"added": added, "removed": removed}


class WatchStore:
    """SQLite store of page snapshots per URL."""

    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, url TEXT, fetched_at REAL, content TEXT)"
        )
        self.conn.commit()

    def save_snapshot(self, url, content, fetched_at=None):
        self.conn.execute(
            "INSERT INTO snapshots (url, fetched_at, content) VALUES (?, ?, ?)",
            (url, fetched_at if fetched_at is not None else time.time(), content),
        )
        self.conn.commit()

    def last_snapshot(self, url):
        """Return (content, fetched_at) of the most recent snapshot, or None."""
        return self.conn.execute(
            "SELECT content, fetched_at FROM snapshots WHERE url = ? ORDER BY id DESC LIMIT 1", (url,)
        ).fetchone()

    def close(self):
        self.conn.close()


def check_url(url, db_path=DB_PATH, fetcher=None):
    """Fetch the page fresh, diff against the last snapshot, store the new one.
    Returns {'first_run', 'changed', 'added', 'removed', 'previous_at'}."""
    if fetcher is None:
        from scrape import get_page_html
        fetcher = lambda u: get_page_html(u, use_cache=False)

    text = normalize_content(fetcher(url))
    store = WatchStore(db_path)
    try:
        previous = store.last_snapshot(url)
        store.save_snapshot(url, text)
    finally:
        store.close()

    if previous is None:
        return {"first_run": True, "changed": False, "added": [], "removed": [], "previous_at": None}

    diff = diff_texts(previous[0], text)
    return {
        "first_run": False,
        "changed": bool(diff["added"] or diff["removed"]),
        "added": diff["added"],
        "removed": diff["removed"],
        "previous_at": previous[1],
    }
