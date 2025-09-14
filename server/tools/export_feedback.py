import os
import csv
import argparse
import sqlite3
from datetime import datetime

try:
    # Prefer package-relative import
    from ..db import get_db_path  # type: ignore
except Exception:
    # Fallback for direct execution from within server/tools/
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from db import get_db_path  # type: ignore


def export_feedback(out_dir: str, like: str | None = None) -> str:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"feedback_export_{ts}.csv")

    db_path = get_db_path()
    query = (
        """
        SELECT file1, file2, label, jaccard, ngram, tfidf, paraphrase,
               re_rank_score, score, risk, model, created_at
        FROM feedback
        {where}
        ORDER BY created_at DESC
        """
    )
    where_clause = ""
    params: list[str] = []
    if like:
        where_clause = "WHERE file1 LIKE ? OR file2 LIKE ?"
        # Use %like% pattern
        pv = f"%{like}%"
        params = [pv, pv]

    with sqlite3.connect(db_path) as conn, open(
        out_path, "w", newline="", encoding="utf-8"
    ) as f:
        cur = conn.cursor()
        cur.execute(query.format(where=where_clause), params)
        rows = cur.fetchall()
        writer = csv.writer(f)
        header = [
            "file1",
            "file2",
            "label",
            "jaccard",
            "ngram",
            "tfidf",
            "paraphrase",
            "re_rank_score",
            "score",
            "risk",
            "model",
            "created_at",
        ]
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Export feedback (positives/negatives) from DB to CSV"
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "artifacts"),
        help="Output directory for CSV (default: server/artifacts)",
    )
    parser.add_argument(
        "--like",
        default=None,
        help="Optional substring to filter by file1/file2 (e.g., 'eoi_solar_setA_')",
    )
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    # Normalize to server/artifacts if relative components exist
    out_dir = os.path.normpath(out_dir)
    path = export_feedback(out_dir, like=args.like)
    print({"export_csv": path})


if __name__ == "__main__":
    main()
