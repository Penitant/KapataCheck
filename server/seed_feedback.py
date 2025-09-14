import os
import re
import glob
import sqlite3
from typing import List, Tuple

# Local imports
from . import db  # init_db, insert_feedback, get_db_path  # type: ignore
from .verify import analyze_files  # type: ignore


def _pair_key(a: str, b: str) -> Tuple[str, str]:
    """Canonicalize pair ordering to avoid duplicates (lexicographic)."""
    return tuple(sorted((a, b)))  # type: ignore


def _already_labeled(file1: str, file2: str) -> bool:
    """Check if a (file1,file2) or (file2,file1) pair exists in DB."""
    path = db.get_db_path()
    if not os.path.exists(path):
        return False
    q = """
        SELECT COUNT(1)
        FROM feedback
        WHERE (file1 = ? AND file2 = ?) OR (file1 = ? AND file2 = ?)
    """
    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        cur.execute(q, (file1, file2, file2, file1))
        n = cur.fetchone()[0]
    return bool(n)


def seed_feedback(
    uploads_dir: str = os.path.join(os.path.dirname(__file__), "uploads"),
    pattern: str = "*.*",
    want_pos: int = 15,
    want_neg: int = 15,
    model_name: str = "all-mpnet-base-v2",
    dry_run: bool = False,
):
    """
    Compute pairwise metrics over uploads and insert balanced labels into DB.

    Heuristics:
      - Positive (label=1) candidates are selected by strong semantic/lexical signals:
          paraphrase >= 0.80 OR (ngram >= 0.45 AND tfidf >= 0.50) OR score >= 0.75
      - Negative (label=0) candidates are selected by low overlap:
          paraphrase <= 0.25 AND tfidf <= 0.30 AND ngram <= 0.30 AND jaccard <= 0.25
      - Fall back: if not enough positives/negatives found, relax thresholds progressively.
    """
    db.init_db()
    files = sorted(glob.glob(os.path.join(uploads_dir, pattern)))
    if len(files) < 2:
        print(f"No pairs to label: found {len(files)} files in {uploads_dir}")
        return {"inserted_pos": 0, "inserted_neg": 0, "total_pairs": 0}

    # Compute metrics
    # Disable paraphrase to avoid requiring heavy TF/Keras deps during seeding
    df = analyze_files(files, model_name=model_name, use_paraphrase=False)

    # Canonicalize file order to prevent duplicates
    df[["file1", "file2"]] = df.apply(
        lambda r: _pair_key(str(r["file1"]), str(r["file2"])),
        axis=1,
        result_type="expand",
    )
    df = df.drop_duplicates(subset=["file1", "file2"]).reset_index(drop=True)

    # Strong positive and clear negative selectors
    # Relax lexical thresholds to allow positive seeding without paraphrase scores
    pos = df[
        (df["paraphrase"] >= 0.80)
        | ((df["ngram"] >= 0.33) & (df["tfidf"] >= 0.45))
        | ((df["jaccard"] >= 0.35) & (df["tfidf"] >= 0.45))
        | (df["score"] >= 0.70)
    ].copy()
    neg = df[
        (df["paraphrase"] <= 0.25)
        & (df["tfidf"] <= 0.30)
        & (df["ngram"] <= 0.30)
        & (df["jaccard"] <= 0.25)
    ].copy()

    # If insufficient, relax thresholds gradually
    if len(pos) < want_pos:
        extra = df[
            (df["paraphrase"] >= 0.70)
            | (df["score"] >= 0.65)
            | ((df["ngram"] >= 0.30) & (df["tfidf"] >= 0.40))
        ].copy()
        pos = (
            __import__("pandas")
            .concat([pos, extra], ignore_index=True)
            .drop_duplicates(subset=["file1", "file2"])  # type: ignore[attr-defined]
        )

    # Heuristic: if filenames look like *_v1.* and *_v2.* with same base, treat as positives
    def _version_base(name: str) -> str:
        stem = os.path.splitext(os.path.basename(name))[0]
        m = re.match(r"^(.*)_v\d+$", stem)
        return m.group(1) if m else stem

    df["_base1"] = df["file1"].apply(_version_base)
    df["_base2"] = df["file2"].apply(_version_base)
    vpos = df[df["_base1"] == df["_base2"]].copy()
    if not vpos.empty:
        pos = (
            __import__("pandas")
            .concat([pos, vpos], ignore_index=True)
            .drop_duplicates(subset=["file1", "file2"])  # type: ignore[attr-defined]
        )
    if len(neg) < want_neg:
        extra_n = df[(df["paraphrase"] <= 0.35) & (df["tfidf"] <= 0.40)].copy()
        neg = (
            __import__("pandas")
            .concat([neg, extra_n], ignore_index=True)
            .drop_duplicates(subset=["file1", "file2"])  # type: ignore[attr-defined]
        )

    # Order by strength (best positives first, clearest negatives first)
    pos = pos.sort_values(["paraphrase", "score", "ngram", "tfidf"], ascending=False)
    neg = neg.sort_values(["paraphrase", "tfidf", "ngram", "jaccard"], ascending=True)

    # Trim to requested counts
    pos = pos.head(want_pos)
    neg = neg.head(want_neg)

    inserted_pos = 0
    inserted_neg = 0
    label_rows: List[Tuple[int, str, str]] = []

    def _insert_row(row, label: int):
        nonlocal inserted_pos, inserted_neg
        f1, f2 = str(row["file1"]), str(row["file2"])
        if _already_labeled(f1, f2):
            return
        payload = {
            "file1": f1,
            "file2": f2,
            "label": int(label),
            "jaccard": float(row.get("jaccard", 0.0)),
            "ngram": float(row.get("ngram", 0.0)),
            "tfidf": float(row.get("tfidf", 0.0)),
            "paraphrase": float(row.get("paraphrase", 0.0)),
            "re_rank_score": float(row.get("re_rank_score", 0.0)),
            "score": float(row.get("score", 0.0)),
            "risk": str(row.get("risk", "")),
            "model": model_name,
        }
        if not dry_run:
            db.insert_feedback(payload)
        if label == 1:
            inserted_pos += 1
        else:
            inserted_neg += 1
        label_rows.append((label, f1, f2))

    # Insert positives then negatives
    for _, r in pos.iterrows():
        _insert_row(r, 1)
    for _, r in neg.iterrows():
        _insert_row(r, 0)

    print(
        f"Labeled examples prepared from {len(files)} files => pairs={len(df)}; inserted pos={inserted_pos}, neg={inserted_neg} (dry_run={dry_run})"
    )
    return {
        "inserted_pos": inserted_pos,
        "inserted_neg": inserted_neg,
        "total_pairs": len(df),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed balanced labeled examples into feedback DB."
    )
    parser.add_argument(
        "--dir",
        default=os.path.join(os.path.dirname(__file__), "uploads"),
        help="Uploads directory",
    )
    parser.add_argument("--pattern", default="*.*", help="Glob pattern for files")
    parser.add_argument("--pos", type=int, default=15, help="Desired positive examples")
    parser.add_argument("--neg", type=int, default=15, help="Desired negative examples")
    parser.add_argument(
        "--model", default="all-mpnet-base-v2", help="Sentence-Transformer model to use"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print counts without inserting",
    )
    args = parser.parse_args()

    seed_feedback(
        uploads_dir=args.dir,
        pattern=args.pattern,
        want_pos=args.pos,
        want_neg=args.neg,
        model_name=args.model,
        dry_run=args.dry_run,
    )
