import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

DATA_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share"),
    "FocusTracker",
)
DB_PATH = os.path.join(DATA_DIR, "focus.db")


@dataclass
class ActivityRow:
    app: str
    title: str
    category: str
    start: float
    duration: float


class Database:
    def __init__(self, path: str = DB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app TEXT NOT NULL,
                title TEXT NOT NULL,
                start REAL NOT NULL,
                duration REAL NOT NULL
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS categories (
                app TEXT PRIMARY KEY,
                category TEXT NOT NULL
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                kind TEXT NOT NULL DEFAULT 'min'
            )"""
        )
        self.conn.commit()

    def add_activity(self, app: str, title: str, start: float, duration: float):
        if duration <= 0:
            return
        self.conn.execute(
            "INSERT INTO activity (app, title, start, duration) VALUES (?, ?, ?, ?)",
            (app, title, start, duration),
        )
        self.conn.commit()

    def set_category(self, app: str, category: str):
        self.conn.execute(
            "INSERT INTO categories (app, category) VALUES (?, ?) "
            "ON CONFLICT(app) DO UPDATE SET category=excluded.category",
            (app, category),
        )
        self.conn.commit()

    def get_categories(self) -> dict:
        return dict(self.conn.execute("SELECT app, category FROM categories").fetchall())

    def category_of(self, app: str) -> str:
        row = self.conn.execute(
            "SELECT category FROM categories WHERE app=?", (app,)
        ).fetchone()
        return row[0] if row else "Neutral"

    def activities_between(self, start_ts: float, end_ts: float) -> list[ActivityRow]:
        cats = self.get_categories()
        rows = self.conn.execute(
            "SELECT app, title, start, duration FROM activity "
            "WHERE start >= ? AND start < ? ORDER BY start",
            (start_ts, end_ts),
        ).fetchall()
        return [
            ActivityRow(app, title, cats.get(app, "Neutral"), start, duration)
            for app, title, start, duration in rows
        ]

    def totals_by_app(self, start_ts: float, end_ts: float) -> list[tuple[str, str, float]]:
        cats = self.get_categories()
        rows = self.conn.execute(
            "SELECT app, SUM(duration) FROM activity "
            "WHERE start >= ? AND start < ? GROUP BY app ORDER BY SUM(duration) DESC",
            (start_ts, end_ts),
        ).fetchall()
        return [(app, cats.get(app, "Neutral"), total) for app, total in rows]

    def totals_by_category(self, start_ts: float, end_ts: float) -> dict:
        result: dict[str, float] = {}
        for _, cat, total in self.totals_by_app(start_ts, end_ts):
            result[cat] = result.get(cat, 0.0) + total
        return result

    def daily_totals(self, days: int = 7) -> list[tuple[str, float, float]]:
        """Returns [(date_label, productive_seconds, distracting_seconds)] for last N days."""
        out = []
        now = datetime.now()
        for i in range(days - 1, -1, -1):
            day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            start_ts = day.timestamp()
            end_ts = (day + timedelta(days=1)).timestamp()
            cats = self.totals_by_category(start_ts, end_ts)
            out.append(
                (day.strftime("%d.%m"), cats.get("Productive", 0.0), cats.get("Distracting", 0.0))
            )
        return out

    def add_goal(self, category: str, minutes: int, kind: str):
        self.conn.execute(
            "INSERT INTO goals (category, minutes, kind) VALUES (?, ?, ?)",
            (category, minutes, kind),
        )
        self.conn.commit()

    def remove_goal(self, goal_id: int):
        self.conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        self.conn.commit()

    def get_goals(self) -> list[tuple[int, str, int, str]]:
        return self.conn.execute("SELECT id, category, minutes, kind FROM goals").fetchall()

    def export_csv(self, path: str, start_ts: float, end_ts: float):
        import csv

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["app", "title", "category", "start", "duration_seconds"])
            for row in self.activities_between(start_ts, end_ts):
                writer.writerow(
                    [
                        row.app,
                        row.title,
                        row.category,
                        datetime.fromtimestamp(row.start).isoformat(),
                        round(row.duration, 1),
                    ]
                )

    def clear_all(self):
        self.conn.execute("DELETE FROM activity")
        self.conn.commit()


def day_bounds(offset_days: int = 0) -> tuple[float, float]:
    day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=offset_days
    )
    return day.timestamp(), (day + timedelta(days=1)).timestamp()


def week_bounds() -> tuple[float, float]:
    now = datetime.now()
    start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start.timestamp(), time.time()
