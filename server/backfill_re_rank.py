"""
Backfill re_rank_score in feedback DB so we can train on 5 features.

Strategy per row with NULL re_rank_score:
- Try to compute a CrossEncoder score using sentence-transformers if available and files can be found.
- Otherwise, compute a proxy using existing features: 0.6*ngram + 0.4*tfidf.

Run:
  python server/backfill_re_rank.py
"""

import os
import sqlite3
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "feedback.db")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def find_file(basename: str) -> Optional[str]:
    # Prefer uploads directory
    p = os.path.join(UPLOADS_DIR, basename)
    if os.path.exists(p):
        return p
    # Try sibling server directory
    p2 = os.path.join(os.path.dirname(__file__), basename)
    if os.path.exists(p2):
        return p2
    # Try repo root
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    p3 = os.path.join(root, basename)
    if os.path.exists(p3):
        return p3
    return None


def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in {".txt", ".md", ".csv"}:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        if ext == ".pdf":
            try:
                import pdfplumber  # type: ignore
            except Exception:
                return ""
            out = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    out.append(page.extract_text() or "")
            return "\n".join(out)
        if ext == ".docx":
            try:
                import docx2txt  # type: ignore
            except Exception:
                return ""
            return docx2txt.process(filepath) or ""
    except Exception:
        return ""
    return ""


def try_cross_encoder(a_text: str, b_text: str) -> Optional[float]:
    try:
        from sentence_transformers import CrossEncoder  # type: ignore
    except Exception:
        return None
    try:
        ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        a = " ".join(a_text.split()[:2048])
        b = " ".join(b_text.split()[:2048])
        s = ce.predict([[a, b]])
        val = float(s[0]) if hasattr(s, "__len__") else float(s)
        # Clamp to [0,1]
        return max(0.0, min(1.0, val))
    except Exception:
        return None


def main():
    if not os.path.exists(DB_PATH):
        print("No DB found; nothing to backfill.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, file1, file2, tfidf, ngram FROM feedback WHERE re_rank_score IS NULL"
        )
        rows = cur.fetchall()
        if not rows:
            print("No rows require backfill.")
            return
        updated = 0
        for id_, f1, f2, tfidf, ngram in rows:
            score = None
            p1 = find_file(f1)
            p2 = find_file(f2)
            if p1 and p2:
                t1 = extract_text(p1)
                t2 = extract_text(p2)
                if t1 and t2:
                    score = try_cross_encoder(t1, t2)
            if score is None:
                # Proxy using lexical features
                t = float(tfidf) if tfidf is not None else 0.0
                n = float(ngram) if ngram is not None else 0.0
                score = 0.6 * n + 0.4 * t
                if score < 0:
                    score = 0.0
                if score > 1:
                    score = 1.0
            cur.execute(
                "UPDATE feedback SET re_rank_score = ? WHERE id = ?",
                (float(score), int(id_)),
            )
            updated += 1
        conn.commit()
        print(f"Backfilled re_rank_score for {updated} rows.")


if __name__ == "__main__":
    main()
