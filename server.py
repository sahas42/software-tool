"""Flask backend for the Compliance Checker Web App."""

import os
import io
import zipfile
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import yaml

from src.compliance_checker.models import UsageRules, DatasetInfo
from src.compliance_checker.codebase_loader import load_codebase
from src.compliance_checker.analyzer import analyze

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIR = BASE_DIR / "webapp"

app = Flask(__name__, static_folder=str(WEBAPP_DIR), static_url_path="")
CORS(app)

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv", ".tox", "dist", "build", ".pytest_cache"}
SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rb", ".rs", ".cs", ".php", ".swift", ".kt"}


def parse_rules_from_yaml(content: str) -> UsageRules:
    raw = yaml.safe_load(content)
    return UsageRules(**raw)


def parse_rules_from_pdf(file_bytes: bytes) -> UsageRules:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        try:
            return parse_rules_from_yaml(text)
        except Exception:
            return UsageRules(
                dataset=DatasetInfo(name="Extracted from PDF", description=text[:500]),
                allowed_uses=["General research (extracted from PDF — please review)"],
                barred_uses=["Any use not covered above (extracted from PDF — please review)"],
            )
    except ImportError:
        raise ValueError("pypdf is not installed. Run: pip install pypdf. Or upload a YAML rules file.")


def load_from_zip(zip_bytes: bytes, extensions: list[str]) -> dict[str, str]:
    """Extract a ZIP archive and return {relative_path: content} for source files."""
    files: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            # Skip directories and hidden/cache paths
            parts = Path(name).parts
            if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
                continue
            if Path(name).suffix in extensions:
                try:
                    content = zf.read(name).decode("utf-8", errors="replace")
                    files[name] = content
                except Exception:
                    pass
    return files


def load_from_uploaded_files(files_list, extensions: list[str]) -> dict[str, str]:
    """Read multiple uploaded source files into a dict."""
    result: dict[str, str] = {}
    for f in files_list:
        fname = f.filename
        if Path(fname).suffix in extensions:
            try:
                content = f.read().decode("utf-8", errors="replace")
                result[fname] = content
            except Exception:
                pass
    return result


@app.route("/")
def index():
    return send_from_directory(str(WEBAPP_DIR), "index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_endpoint():
    api_key = request.form.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
    codebase_type = request.form.get("codebase_type", "github")  # github | files | zip | folder
    extensions_raw = request.form.get("extensions", ".py,.js,.ts,.java,.cpp,.c,.go,.rb,.rs")
    extensions = [e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in extensions_raw.split(",")]

    if not api_key:
        return jsonify({"error": "Gemini API key is required."}), 400

    # --- Parse rules ---
    rules_file = request.files.get("rules_file")
    if not rules_file:
        return jsonify({"error": "Rules file (YAML or PDF) is required."}), 400

    filename = rules_file.filename.lower()
    file_bytes = rules_file.read()
    try:
        if filename.endswith((".yaml", ".yml")):
            rules = parse_rules_from_yaml(file_bytes.decode("utf-8"))
        elif filename.endswith(".pdf"):
            rules = parse_rules_from_pdf(file_bytes)
        else:
            try:
                rules = parse_rules_from_yaml(file_bytes.decode("utf-8", errors="ignore"))
            except Exception:
                rules = parse_rules_from_pdf(file_bytes)
    except Exception as e:
        return jsonify({"error": f"Failed to parse rules file: {e}"}), 422

    # --- Load codebase ---
    try:
        if codebase_type == "github":
            codebase_url = request.form.get("codebase_url", "").strip()
            if not codebase_url:
                return jsonify({"error": "GitHub URL is required."}), 400
            codebase = load_codebase(codebase_url)

        elif codebase_type == "zip":
            zip_file = request.files.get("codebase_zip")
            if not zip_file:
                return jsonify({"error": "ZIP file is required."}), 400
            codebase = load_from_zip(zip_file.read(), extensions)

        elif codebase_type in ("files", "folder"):
            uploaded = request.files.getlist("codebase_files")
            if not uploaded:
                return jsonify({"error": "No files uploaded."}), 400
            codebase = load_from_uploaded_files(uploaded, extensions)

        else:
            return jsonify({"error": f"Unknown codebase_type: {codebase_type}"}), 400

    except Exception as e:
        return jsonify({"error": f"Failed to load codebase: {e}"}), 422

    if not codebase:
        return jsonify({"error": "No source files found. Check file types / extensions."}), 422

    # --- Analyze ---
    try:
        report = analyze(rules, codebase, api_key)
    except Exception as e:
        return jsonify({"error": f"Gemini API analysis failed: {e}"}), 500

    return jsonify(report.model_dump()), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)
