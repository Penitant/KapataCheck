import os
import sqlite3
from typing import Optional, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "feedback.db")


def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file1 TEXT NOT NULL,
                file2 TEXT NOT NULL,
                label INTEGER NOT NULL,
                jaccard REAL,
                ngram REAL,
                tfidf REAL,
                paraphrase REAL,
                score REAL,
                risk TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Backward-compatible migration: add re_rank_score if missing
        try:
            c.execute("PRAGMA table_info(feedback)")
            cols = [row[1] for row in c.fetchall()]
            if "re_rank_score" not in cols:
                c.execute("ALTER TABLE feedback ADD COLUMN re_rank_score REAL")
        except Exception:
            pass
        conn.commit()


def insert_feedback(row: Dict[str, Any]) -> int:
    required = {"file1", "file2", "label"}
    missing = required - set(row)
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO feedback (file1, file2, label, jaccard, ngram, tfidf, paraphrase, score, risk, model, re_rank_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("file1"),
                row.get("file2"),
                int(row.get("label")),
                row.get("jaccard"),
                row.get("ngram"),
                row.get("tfidf"),
                row.get("paraphrase"),
                row.get("score"),
                row.get("risk"),
                row.get("model"),
                row.get("re_rank_score"),
            ),
        )
        conn.commit()
        return int(c.lastrowid)


def get_db_path() -> str:
    return DB_PATH
