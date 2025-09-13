import os
import glob
import re
import traceback
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer, util


# --- Text cleaning and classical similarities ---
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def jaccard_similarity(a: str, b: str) -> float:
    """
    What it catches: direct copy/paste at the word level, shared boilerplate, and repeated phrases.
    Why useful: very interpretable signal—“how much of the vocabulary is shared.” Great for templated or lightly tweaked documents.
    Limits: synonyms/rewording drop the score; sensitive to tokenization.
    """
    set_a, set_b = set(a.split()), set(b.split())
    intersection = set_a & set_b
    union = set_a | set_b
    if union:
        return len(intersection) / len(union)
    return 0.0


def ngram_similarity(a: str, b: str, n: int = 4) -> float:
    """
    What it catches: near-duplicates with small obfuscations (e.g., punctuation changes, spacing, minor typos, pluralization); detects reused strings even when token boundaries shift.
    Why useful: robust to superficial edits; stronger indicator of literal copying than Jaccard.
    Limits: less semantic; can be noisy if documents share many short common substrings.
    """
    ngrams = lambda s: set([s[i : i + n] for i in range(max(0, len(s) - n + 1))])
    ngrams_a, ngrams_b = ngrams(a), ngrams(b)
    intersection = ngrams_a & ngrams_b
    union = ngrams_a | ngrams_b
    if union:
        return len(intersection) / len(union)
    return 0.0


def tfidf_cosine_similarity(texts: List[str]) -> np.ndarray:
    """
    What it catches: topical and phrase-level overlap beyond exact copy—weights distinctive terms more than common ones.
    Why useful: mitigates stopword effects; scalable and fast, good “broad net” across many files.
    Limits: still lexical; paraphrases or synonym swaps reduce similarity.
    """
    if not texts:
        return np.zeros((0, 0))
    tfidf = TfidfVectorizer().fit_transform(texts)
    return (tfidf * tfidf.T).A


def _chunk_words(text: str, words_per_chunk: int = 200) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    return [
        " ".join(words[i : i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ]


def paraphrase_similarity(a: str, b: str, model: SentenceTransformer) -> float:
    """
    What it catches: reworded content, paraphrases, and semantically equivalent passages (the typical way to evade copy detection).
    Why useful: goes beyond lexical matching; captures meaning-level similarity.
    Design detail: we chunk text and take the 90th percentile of chunk×chunk cosine scores to highlight strong local matches without being diluted by unrelated sections (common in long docs).
    Limits: heavier compute; can over-score generic, high-level language; needs careful thresholds.
    """
    blocks_a = _chunk_words(a, 200)
    blocks_b = _chunk_words(b, 200)
    if not any(blocks_a) or not any(blocks_b):
        return 0.0
    emb_a = model.encode(blocks_a, convert_to_tensor=True, show_progress_bar=False)
    emb_b = model.encode(blocks_b, convert_to_tensor=True, show_progress_bar=False)
    sim_matrix = util.pytorch_cos_sim(emb_a, emb_b).cpu().numpy()
    return float(np.percentile(sim_matrix, 90))


_MODEL_CACHE: Dict[str, SentenceTransformer] = {}


def get_model(
    model_name: str = "all-mpnet-base-v2",  # paraphrase-multilingual-mpnet-base-v2
) -> SentenceTransformer:
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def _risk_label(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.70:
        return "Medium"
    if score >= 0.50:
        return "Low"
    return "Normal"


def compare_texts(
    texts: List[str],
    filenames: Optional[List[str]] = None,
    weights: Optional[Dict[str, float]] = None,
    model_name: str = "all-mpnet-base-v2",
) -> pd.DataFrame:
    if filenames is None:
        filenames = [f"doc_{i}.txt" for i in range(len(texts))]
    if weights is None:
        weights = {"ngram": 0.45, "tfidf": 0.25, "jaccard": 0.15, "para": 0.15}

    model = get_model(model_name)
    tfidf_sim_matrix = (
        tfidf_cosine_similarity(texts)
        if len(texts) > 1
        else np.zeros((len(texts), len(texts)))
    )

    rows: List[Dict] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            jac = jaccard_similarity(texts[i], texts[j])
            ngram = ngram_similarity(texts[i], texts[j])
            tfidf = float(tfidf_sim_matrix[i, j]) if tfidf_sim_matrix.size else 0.0
            para = paraphrase_similarity(texts[i], texts[j], model)
            score = (
                weights.get("ngram", 0) * ngram
                + weights.get("tfidf", 0) * tfidf
                + weights.get("jaccard", 0) * jac
                + weights.get("para", 0) * para
            )
            rows.append(
                {
                    "file1": filenames[i],
                    "file2": filenames[j],
                    "jaccard": jac,
                    "ngram": ngram,
                    "tfidf": tfidf,
                    "paraphrase": para,
                    "score": score,
                    "risk": _risk_label(score),
                }
            )
    return pd.DataFrame(rows)


def analyze_files(
    filepaths: List[str],
    include_non_text: bool = True,
    model_name: str = "all-mpnet-base-v2",
) -> pd.DataFrame:
    texts: List[str] = []
    filenames: List[str] = []
    for fp in filepaths:
        if include_non_text:
            raw = extract_text(fp)
        else:
            ext = os.path.splitext(fp)[1].lower()
            if ext in {".txt", ".md", ".csv"}:
                raw = open(fp, "r", encoding="utf-8", errors="ignore").read()
            else:
                raw = ""
        texts.append(clean_text(raw))
        filenames.append(os.path.basename(fp))
    return compare_texts(texts, filenames=filenames, model_name=model_name)


def compare_all_files(
    folder_path: str,
    pattern: str = "*.*",
    save_csv: Optional[str] = "similarity_report.csv",
    model_name: str = "all-mpnet-base-v2",
) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(folder_path, pattern)))
    df = analyze_files(files, model_name=model_name)
    flagged = df[df["risk"].isin(["High", "Medium"])].sort_values(
        "score", ascending=False
    )
    if save_csv:
        flagged.to_csv(save_csv, index=False)
    print(flagged)
    return flagged


# --- Document Extraction ---
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
        traceback.print_exc()
    return ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze tender documents for similarity and risk."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="server/uploads",
        help="Path to folder containing documents (PDF/DOCX/TXT). Defaults to server/uploads",
    )
    parser.add_argument(
        "--pattern", default="*.*", help="Glob pattern to match files inside folder"
    )
    parser.add_argument(
        "--csv", default="similarity_report.csv", help="CSV output path (empty to skip)"
    )
    parser.add_argument(
        "--model", default="all-mpnet-base-v2", help="Sentence-Transformer model to use"
    )
    args = parser.parse_args()

    csv_path = args.csv if args.csv else None
    compare_all_files(
        args.folder,
        pattern=args.pattern,
        save_csv=csv_path,
        model_name=args.model,
    )
