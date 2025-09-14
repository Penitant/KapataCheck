# Chakshu – EOI similarity detection service

Chakshu surfaces potential coordination or reuse across Expressions of Interest (EOIs) and similar tender documents. It combines fast lexical signals with semantic models, re‑ranking, and light self‑learning. A calibrated probability‑like score and risk label are produced per file pair.

Highlights:
- Multi‑signal features: Jaccard, char n‑grams, TF‑IDF cosine, paraphrase embeddings (optional), CrossEncoder re‑rank (optional)
- Diagnostics that also influence final score: BM25 pair score, ANN cosine, SimHash, MinHash, clustering co‑membership
- Self‑learning from feedback with hot‑reloaded model and calibration
- Graceful degradation if optional deps aren’t installed

## Project layout

- `server/server.py` – Flask API (/verify, /feedback, /retrain, /review)
- `server/verify.py` – Text extraction and feature computation (lexical, semantic, CE, diagnostics)
- `server/learn.py` – Final scoring pipeline (model + calibration + diagnostic nudge, or fallback weights)
- `server/train_feedback.py` – Trains model from SQLite feedback
- `server/calibration.py` – Fits Platt/Isotonic calibrators
- `server/db.py` – SQLite initialization and feedback helpers
- `server/simple_lr.py` – Pure‑Python logistic regression and dummy classifier
- Artifacts/data: `server/uploads/`, `server/data/feedback.db`, `server/models/*`, `server/artifacts/*`

## Setup

1) Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
 .\.venv\Scripts\Activate.ps1
```

2) Install dependencies. Prefer `requirements.txt`, which separates core vs optional installs. If you want a minimal core without extras, install only what you need.

```powershell
# Core (server + core features)
pip install flask flask-cors numpy pandas scikit-learn

# Optional accuracy/features (install as needed)
pip install sentence-transformers

# Optional retrieval/diagnostics
pip install rank-bm25 datasketch networkx python-louvain

# Optional file formats
pip install pdfplumber docx2txt
```

3) (Optional) GPU: install a CUDA‑enabled PyTorch compatible with your driver for faster embeddings/CE.

## Run the server

```powershell
python -m server.server
```

Then POST to `http://127.0.0.1:5000/verify` with multipart form‑data field `files` (attach 2+ files).

Feature toggles via query params:
- `?model=all-mpnet-base-v2` – Sentence‑Transformers backbone
- `?paraphrase=1` – paraphrase embeddings (heavier)
- `?ce=1` – CrossEncoder re‑rank over candidates (heavier)
- `?hash=1` – SimHash/MinHash diagnostics
- `?hybrid=1` – BM25 + ANN embeddings for retrieval/diagnostics
- `?cluster=1` – Louvain clustering over ANN graph
- `?ce_top_k=10` – top‑K candidates per document for CE
- `?keep=1` – keep uploaded files (default deletes them after processing)
 - `?timings=1` – include simple timing info in the response (e.g., analyze_ms)

Response per pair includes all feature values, the final `score` (0–1), and a `risk` label.

Example (PowerShell):

```powershell
$files = @(
   @{ name = 'files'; filename = 'a.pdf'; content = [IO.File]::ReadAllBytes('a.pdf') },
   @{ name = 'files'; filename = 'b.docx'; content = [IO.File]::ReadAllBytes('b.docx') }
)
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/verify?model=all-mpnet-base-v2&paraphrase=1&ce=1' -Method Post -Form $files
```

## Scoring and risk

Final score is produced by `server/learn.py`:
- If a trained model is loaded:
   1) Predict probability from core features (4D or 5D): `[jaccard, tfidf, ngram, paraphrase, re_rank_score?]`
   2) Apply calibration if available (prefer Platt, else Isotonic)
   3) Add a small diagnostic nudge from: `bm25_pair`, `ann_cosine`, `simhash`, `minhash`, `cluster_same` (then clamp to [0,1])
- If no model is loaded: use a weighted blend across core features plus diagnostics (small weights), renormalized over available keys.

Default risk thresholds:
- High ≥ 0.85, Medium ≥ 0.70, Low ≥ 0.50, else Normal

You can override fallback weights via `server/artifacts/weights.json`:

```json
{
   "feature_order": [
      "jaccard","tfidf","ngram","paraphrase","re_rank_score",
      "bm25_pair","ann_cosine","simhash","minhash","cluster_same"
   ],
   "weights": [0.18,0.27,0.23,0.22,0.06,0.02,0.015,0.01,0.01,0.005],
   "notes": "Optional metadata"
}
```

## Training and calibration

1) Submit feedback:
- POST `/feedback` (JSON): `file1`, `file2`, `label` (1 or 0). You can include feature values for provenance.
- Stored in `server/data/feedback.db` (SQLite). `/verify` response includes `original_file1/2` for traceability.

2) Train a model:

```powershell
python -m server.train_feedback
```

- Tries LightGBM (if installed); otherwise trains a pure‑Python logistic regression from `server/simple_lr.py`.
- Model persisted to `server/models/feedback_lr.pkl` and hot‑reloaded by the server.
- Core features: 4D or 5D (+`re_rank_score` if CE was used during labeling/training).

3) Calibrate (optional but recommended):

```powershell
python -m server.calibration --split 0.2
```

- Saves `server/models/platt.pkl` and `server/models/isotonic.pkl`.
- `learn.py` applies Platt first (if present), else Isotonic.

4) Evaluate (optional):

```powershell
python -m server.eval_model
```

Prints ROC‑AUC and a risk distribution.

## CLI (batch compare)

Run analysis directly on a folder and write a CSV of Medium/High risk pairs:

```powershell
python server/verify.py "C:\path\to\folder" --pattern "*.*" --model all-mpnet-base-v2 --csv similarity_report.csv --paraphrase --cross-encoder
```

## Optional dependencies and graceful fallback

Optional packages are imported lazily. If missing, the related feature returns zeros and the service continues:
- Semantic: `sentence-transformers` (and its deps)
- Retrieval/diagnostics: `rank-bm25`, `datasketch`
- Formats: `pdfplumber` (PDF), `docx2txt` (DOCX)
- Clustering: `networkx`, `python-louvain`

TF‑IDF fallback: `TfidfVectorizer` is lazily imported inside the function. If `scikit-learn` isn’t installed, TF‑IDF gracefully falls back to a zero matrix (feature contributes 0) instead of failing the import.

CE candidates: If BM25/ANN aren’t available, CE runs on all pairs (higher cost, similar accuracy), and the `re_rank_score` is still computed for those pairs.

## Troubleshooting

- Missing imports (flask, numpy, sklearn, etc.): install required packages into your venv.
- CE/paraphrase are slow without GPU: keep them off or reduce `ce_top_k`.
- Large documents: the CE input is truncated to ~2048 tokens/side to control cost.
- Windows paths: quote paths with spaces in PowerShell (as shown above).
- Keep uploads for audit: add `?keep=1` to `/verify`. Files are otherwise deleted post‑processing.

## License

Internal or project‑specific; add a LICENSE if distributing.
