# Import necessary modules
from flask import Flask, jsonify, request
from flask_cors import CORS
from os import makedirs, path
import tempfile
import uuid
from typing import List

try:
    from .verify import analyze_files
except Exception:
    import sys, os

    sys.path.append(os.path.dirname(__file__))
    from verify import analyze_files  # type: ignore

# App initialization
app = Flask(__name__)

# Allow only a specific frontend origin; no cookies/credentials are needed
ALLOWED_ORIGIN = "http://localhost:5173"
CORS(app, resources={r"/*": {"origins": [ALLOWED_ORIGIN]}}, supports_credentials=False)

# Set upload folder
UPLOAD_FOLDER = "server/uploads"
makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Define routes
@app.route("/")
def home():
    return """
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Chakshu | Backend</title>
        </head>
        <body>
            <h1>Welcome to Chakshu Backend!</h1>
        </body>
        </html>
    """


@app.route("/verify", methods=["POST"])
def verify():
    """Accepts multiple files and returns similarity analysis.
    Multipart form field name: 'files'. Returns list of pairwise results.
    """
    if "files" not in request.files:
        return jsonify({"error": "No files provided (use form field 'files')"}), 400

    files = request.files.getlist("files")
    saved_paths: List[str] = []
    for f in files:
        if not f.filename:
            continue

        ext = path.splitext(f.filename)[1]
        unique = f"{uuid.uuid4().hex}{ext}"
        dest = path.join(app.config["UPLOAD_FOLDER"], unique)
        f.save(dest)
        saved_paths.append(dest)

    if len(saved_paths) < 2:
        return jsonify({"error": "Need at least two files for comparison"}), 400

    model_name = request.args.get("model") or "all-mpnet-base-v2"
    df = analyze_files(saved_paths, model_name=model_name)

    results = df.to_dict(orient="records")
    return jsonify({"model": model_name, "count": len(results), "results": results})


# Run the app
if __name__ == "__main__":
    app.run()
