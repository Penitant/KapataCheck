import os
import glob
import re
import traceback
from typing import List, Dict, Optional, Any

import numpy as np
import pandas as pd

# Note: sentence_transformers is lazily imported inside functions to avoid heavy deps at import time
try:
    from .learn import get_smart_score
except Exception:
    # Fallback when running as script
    import sys, os

    sys.path.append(os.path.dirname(__file__))
    from learn import get_smart_score  # type: ignore


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
    n = len(texts)
    if n == 0:
        return np.zeros((0, 0))
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    except Exception:
        # sklearn not available: degrade gracefully
        return np.zeros((n, n))
    tfidf = TfidfVectorizer().fit_transform(texts)
    # (n_docs x n_terms) * (n_terms x n_docs) -> (n_docs x n_docs) sparse matrix
    # Convert to dense ndarray in a portable way
    return (tfidf * tfidf.T).toarray()


def _chunk_words(text: str, words_per_chunk: int = 200) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    return [
        " ".join(words[i : i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ]


def paraphrase_similarity(a: str, b: str, model: Any) -> float:
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
    # Lazy import to avoid importing transformers unless needed
    from sentence_transformers import util  # type: ignore

    emb_a = model.encode(blocks_a, convert_to_tensor=True, show_progress_bar=False)
    emb_b = model.encode(blocks_b, convert_to_tensor=True, show_progress_bar=False)
    sim_matrix = util.pytorch_cos_sim(emb_a, emb_b).cpu().numpy()
    return float(np.percentile(sim_matrix, 90))


_MODEL_CACHE: Dict[str, Any] = {}
_CROSS_ENCODER_CACHE: Dict[str, Any] = {}


def get_model(
    model_name: str = "all-mpnet-base-v2",  # paraphrase-multilingual-mpnet-base-v2
) -> Any:
    """Lazy-load SentenceTransformer to avoid importing transformers at module import time."""
    if model_name not in _MODEL_CACHE:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "SentenceTransformer is required for paraphrase similarity but failed to import."
            ) from e
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> Any:
    """Lazy-load CrossEncoder for pairwise re-ranking and cache it."""
    if model_name not in _CROSS_ENCODER_CACHE:
        from sentence_transformers import CrossEncoder  # type: ignore

        _CROSS_ENCODER_CACHE[model_name] = CrossEncoder(model_name)
    return _CROSS_ENCODER_CACHE[model_name]


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
    model_name: str = "all-mpnet-base-v2",
    use_paraphrase: bool = False,
    use_cross_encoder: bool = False,
    use_hash: bool = False,
    use_hybrid: bool = False,
    use_clustering: bool = False,
    raw_texts: Optional[List[str]] = None,
    ce_top_k: int = 10,
    diag_level: str = "med",
) -> pd.DataFrame:
    if filenames is None:
        filenames = [f"doc_{i}.txt" for i in range(len(texts))]

    model = None
    if use_paraphrase:
        try:
            model = get_model(model_name)
        except Exception:
            model = None
    tfidf_sim_matrix = (
        tfidf_cosine_similarity(texts)
        if len(texts) > 1
        else np.zeros((len(texts), len(texts)))
    )

    # Optional per-document prep for hashing and hybrid features
    tokens: List[List[str]] = []
    simhashes: List[int] = []
    minhashes: List[Any] = []
    bm25 = None
    bm25_scores: List[List[float]] = []
    embeddings = None

    if use_hash or use_hybrid or use_clustering:
        # Tokenize once
        tokens = [t.split() for t in texts]

    # Hashing features
    if use_hash:
        # SimHash
        simhashes = []
        import hashlib

        for toks in tokens:
            if not toks:
                simhashes.append(0)
                continue
            bit_acc = [0] * 64
            for t in toks:
                h = int(
                    hashlib.blake2b(t.encode("utf-8"), digest_size=8).hexdigest(), 16
                )
                for i in range(64):
                    bit_acc[i] += 1 if (h >> i) & 1 else -1
            out = 0
            for i in range(64):
                if bit_acc[i] >= 0:
                    out |= 1 << i
            simhashes.append(out)
        # MinHash (if available)
        try:
            from datasketch import MinHash  # type: ignore

            minhashes = []
            for toks in tokens:
                mh = MinHash(num_perm=64)
                for t in toks:
                    mh.update(t.encode("utf-8"))
                minhashes.append(mh)
        except Exception:
            minhashes = [None] * len(tokens)

    # Hybrid: BM25 per-pair score (symmetrized) + ANN cosine via embeddings
    if use_hybrid or use_clustering or use_cross_encoder:
        # BM25
        try:
            from rank_bm25 import BM25Okapi  # type: ignore

            bm25 = BM25Okapi(tokens)
            # Precompute normalized scores for each query document
            for i in range(len(tokens)):
                scores = list(bm25.get_scores(tokens[i]))
                max_s = max(scores) if scores else 1.0
                if max_s <= 0:
                    max_s = 1.0
                bm25_scores.append([float(s) / float(max_s) for s in scores])
        except Exception:
            bm25 = None
            bm25_scores = []
        # Embeddings
        try:
            model_e = get_model(model_name)
            embeddings = model_e.encode(texts, normalize_embeddings=True)
        except Exception:
            embeddings = None

    # Build CE candidate pairs using BM25/ANN top-K per document (i<j). If no signals, fallback to all pairs.
    candidate_pairs: set = set()
    n_docs = len(texts)
    if use_cross_encoder and ce_top_k and (bm25_scores or embeddings is not None):
        try:
            import numpy as _np
        except Exception:
            _np = None  # type: ignore
        E = None
        if embeddings is not None and _np is not None:
            try:
                E = _np.asarray(embeddings, dtype=float)
            except Exception:
                E = None
        for i in range(n_docs):
            cand = set()
            # BM25 top-K
            if bm25_scores:
                try:
                    scores = list(bm25_scores[i])
                    if scores:
                        scores[i] = -1.0
                        # get indices of top ce_top_k
                        top_idx = sorted(
                            range(n_docs), key=lambda j: scores[j], reverse=True
                        )[:ce_top_k]
                        cand.update(top_idx)
                except Exception:
                    pass
            # ANN cosine top-K
            if E is not None:
                try:
                    sims = E @ E[i]
                    sims[i] = -1.0
                    top_idx = list(
                        _np.argpartition(-sims, range(min(ce_top_k, n_docs - 1)))[
                            :ce_top_k
                        ]
                    )
                    cand.update(top_idx)
                except Exception:
                    # Fallback per-pair in loop
                    pass
            for j in cand:
                if 0 <= j < n_docs and j != i:
                    a, b = (i, j) if i < j else (j, i)
                    candidate_pairs.add((a, b))

    # Optional clustering (Louvain): build simple similarity graph from ANN cosine
    cluster_same_map: Dict[tuple, int] = {}
    if use_clustering and embeddings is not None:
        try:
            import networkx as nx  # type: ignore

            try:
                import community as community_louvain  # type: ignore
            except Exception:
                community_louvain = None  # type: ignore
            G = nx.Graph()
            for i, f in enumerate(filenames):
                G.add_node(i, file=f)
            # Add edges for moderately similar pairs by ANN cosine
            n = len(texts)
            for i in range(n):
                for j in range(i + 1, n):
                    if embeddings is not None:
                        sim = float(np.dot(embeddings[i], embeddings[j]))
                        if sim >= 0.6:
                            G.add_edge(i, j, weight=sim)
            if G.number_of_edges() > 0 and community_louvain is not None:
                part = community_louvain.best_partition(G)  # node -> community id
                for i in range(n):
                    for j in range(i + 1, n):
                        same = 1 if part.get(i) == part.get(j) else 0
                        cluster_same_map[(i, j)] = same
        except Exception:
            cluster_same_map = {}

    # Collect rows and optionally CE inputs; we'll batch CE for efficiency
    rows: List[Dict] = []
    ce_inputs: List[List[str]] = []
    ce_row_indexes: List[int] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            jac = jaccard_similarity(texts[i], texts[j])
            ngram = ngram_similarity(texts[i], texts[j])
            tfidf = float(tfidf_sim_matrix[i, j]) if tfidf_sim_matrix.size else 0.0
            # Paraphrase via transformer (optional); if model/encode fails, fall back to 0.0 so API does not 500
            para = 0.0
            if use_paraphrase and model is not None:
                try:
                    para = paraphrase_similarity(texts[i], texts[j], model)
                except Exception:
                    para = 0.0
            # Hashing features per pair
            simhash_sim = 0.0
            minhash_sim = 0.0
            if use_hash and simhashes:
                a, b = simhashes[i], simhashes[j]
                ham = bin(a ^ b).count("1")
                simhash_sim = 1.0 - (ham / 64.0)
            if (
                use_hash
                and minhashes
                and minhashes[i] is not None
                and minhashes[j] is not None
            ):
                try:
                    minhash_sim = float(minhashes[i].jaccard(minhashes[j]))
                except Exception:
                    minhash_sim = 0.0
            # Hybrid per-pair scores
            bm25_pair = 0.0
            ann_cos = 0.0
            if (use_hybrid or use_clustering) and bm25_scores:
                try:
                    s_ij = bm25_scores[i][j]
                    s_ji = bm25_scores[j][i]
                    bm25_pair = 0.5 * (float(s_ij) + float(s_ji))
                except Exception:
                    bm25_pair = 0.0
            if (use_hybrid or use_clustering) and embeddings is not None:
                try:
                    ann_cos = float(np.dot(embeddings[i], embeddings[j]))
                except Exception:
                    ann_cos = 0.0
            re_rank = 0.0
            if use_cross_encoder:
                # Only schedule CE if (i,j) is a candidate or if no candidates were built
                is_candidate = True
                if candidate_pairs:
                    is_candidate = (i, j) in candidate_pairs
                if is_candidate:
                    a_src = raw_texts[i] if raw_texts is not None else texts[i]
                    b_src = raw_texts[j] if raw_texts is not None else texts[j]
                    a_trunc = " ".join(a_src.split()[:2048])
                    b_trunc = " ".join(b_src.split()[:2048])
                    ce_inputs.append([a_trunc, b_trunc])
                    ce_row_indexes.append(len(rows))
            # Compute score using learned model if available, otherwise fallback weights
            score = 0.0  # placeholder until CE (if any) is applied below
            rows.append(
                {
                    "file1": filenames[i],
                    "file2": filenames[j],
                    "jaccard": jac,
                    "ngram": ngram,
                    "tfidf": tfidf,
                    "paraphrase": para,
                    "re_rank_score": re_rank,
                    "bm25_pair": bm25_pair,
                    "ann_cosine": ann_cos,
                    "simhash": simhash_sim,
                    "minhash": minhash_sim,
                    "cluster_same": (
                        int(cluster_same_map.get((i, j), 0)) if use_clustering else 0
                    ),
                    "score": score,
                    "risk": "",
                }
            )
    # If CE is enabled, run it in batch and fill re_rank_score
    if use_cross_encoder and ce_inputs:
        try:
            ce = get_cross_encoder()
            ce_scores = ce.predict(ce_inputs)
            # Clamp to [0,1]
            norm = [float(max(0.0, min(1.0, float(s)))) for s in ce_scores]
            for idx, s in zip(ce_row_indexes, norm):
                rows[idx]["re_rank_score"] = s
        except Exception:
            pass
    # Finalize score and risk with available features (include diagnostics to influence score)
    for r in rows:
        score = get_smart_score(
            {
                "jaccard": r["jaccard"],
                "ngram": r["ngram"],
                "tfidf": r["tfidf"],
                "paraphrase": r["paraphrase"],
                "re_rank_score": r.get("re_rank_score", 0.0),
                "bm25_pair": r.get("bm25_pair", 0.0),
                "ann_cosine": r.get("ann_cosine", 0.0),
                "simhash": r.get("simhash", 0.0),
                "minhash": r.get("minhash", 0.0),
                "cluster_same": float(r.get("cluster_same", 0)),
                "__diag_level__": diag_level,
            }
        )
        r["score"] = score
        r["risk"] = _risk_label(score)
    return pd.DataFrame(rows)


def analyze_files(
    filepaths: List[str],
    include_non_text: bool = True,
    model_name: str = "all-mpnet-base-v2",
    use_paraphrase: bool = False,
    use_cross_encoder: bool = False,
    use_hash: bool = False,
    use_hybrid: bool = False,
    use_clustering: bool = False,
    ce_top_k: int = 10,
    diag_level: str = "med",
) -> pd.DataFrame:
    texts: List[str] = []
    raw_texts: List[str] = []
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
        raw_texts.append(raw)
        texts.append(clean_text(raw))
        filenames.append(os.path.basename(fp))
    return compare_texts(
        texts,
        filenames=filenames,
        model_name=model_name,
        use_paraphrase=use_paraphrase,
        use_cross_encoder=use_cross_encoder,
        use_hash=use_hash,
        use_hybrid=use_hybrid,
        use_clustering=use_clustering,
        raw_texts=raw_texts,
        ce_top_k=ce_top_k,
        diag_level=diag_level,
    )


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


# Note: Hybrid indexing and clustering removed for simplicity.


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze documents for similarity and risk (lightweight)."
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
    parser.add_argument(
        "--paraphrase", action="store_true", help="Enable paraphrase similarity"
    )
    parser.add_argument(
        "--cross-encoder",
        action="store_true",
        help="Enable cross-encoder re-rank score",
    )
    args = parser.parse_args()

    compare_all_files(
        args.folder,
        pattern=args.pattern,
        save_csv=(args.csv if args.csv else None),
        model_name=args.model,
    )
