# Chakshu

AI-powered similarity analysis for expressions of interest documents to help detect potential collusion. It compares uploaded documents using multiple layers: token overlap (Jaccard), character n-grams, TF-IDF/cosine and transformer-based semantic similarity (Sentence-Transformers), then flags pairs with elevated risk.

## Setup

1. Create a virtual environment and install dependencies:

   - Windows PowerShell

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. (Optional) GPU: install CUDA-enabled PyTorch per your GPU/driver.

## Run the server

```powershell
python -m server.server
```

Then open POST http://127.0.0.1:5000/verify with multipart form-data field `files` (you can attach 2+ files).
You can optionally select the embedding model using a query param, e.g. `?model=all-mpnet-base-v2`.

Response includes pairwise results with per-metric scores, final score, and risk label.

Example using PowerShell Invoke-RestMethod (optional):

```powershell
$files = @(
	@{ name = 'files'; filename = 'a.pdf'; content = [System.IO.File]::ReadAllBytes('a.pdf') },
	@{ name = 'files'; filename = 'b.docx'; content = [System.IO.File]::ReadAllBytes('b.docx') }
)
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/verify?model=all-mpnet-base-v2' -Method Post -Form $files
```

## CLI usage (batch compare)

You can also run analysis directly on a folder (defaults to `server/uploads` if not provided):

```powershell
python server/verify.py "C:\path\to\folder" --pattern "*.*" --model all-mpnet-base-v2 --csv similarity_report.csv
```

This will write `similarity_report.csv` with Medium/High risk pairs.

## Notes

- Supported inputs: .txt, .md, .csv, .pdf, .docx (PDF/DOCX require optional packages as listed).
- Default model: `all-mpnet-base-v2` (strong accuracy for English). You can switch via `--model` or the API query parameter.
- Thresholds/weights can be adjusted in `server/verify.py`.
