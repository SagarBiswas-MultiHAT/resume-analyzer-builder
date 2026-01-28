import os
import re
import tempfile

import spacy
from docx import Document
from dotenv import find_dotenv, load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from pdfminer.high_level import extract_text
from werkzeug.utils import secure_filename

# Load environment variables from .env files (root + backend) if present.
# We attempt multiple strategies to reduce surprises on Windows / different CWDs.
load_dotenv()  # default search (current working directory upward)
found_global = find_dotenv(usecwd=True)
if found_global:
    load_dotenv(found_global, override=False)
backend_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.isfile(backend_env_path):
    load_dotenv(backend_env_path, override=False)

app = Flask(__name__)

# Restrict CORS to localhost by default (safer for dev). Override with CORS_ORIGINS env.
_cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000"
)
_cors_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
CORS(app, origins=_cors_origins)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB upload limit

# Load the spaCy model
nlp = spacy.load('en_core_web_sm')

# Flask application for resume analysis
# This application provides endpoints for uploading resumes and serving static files

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # default model; override via env
_fallback_env = os.getenv("GROQ_FALLBACK_MODELS", "")
GROQ_FALLBACK_MODELS = [m.strip() for m in _fallback_env.split(",") if m.strip()]
if not GROQ_FALLBACK_MODELS:
    # Safe defaults if the primary model is blocked at the project level
    GROQ_FALLBACK_MODELS = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ]
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # pull from environment / .env


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"[WARN] Invalid {name} value: {raw}. Using default {default}.")
        return default


# Lower temperature yields more consistent ratings and suggestions.
GROQ_TEMPERATURE = _get_float_env("GROQ_TEMPERATURE", 0.2)
GROQ_TOP_P = _get_float_env("GROQ_TOP_P", 0.9)

# Accept common alias environment variable names as fallback (helps misnamed vars)
if not GROQ_API_KEY:
    for _alt in ["GROQ_KEY", "GROQ_APIKEY", "GROQ_SECRET", "GROQ"]:
        _val = os.getenv(_alt)
        if _val:
            GROQ_API_KEY = _val
            print(f"[INFO] Using alias env var {_alt} for GROQ_API_KEY")
            break

# Optional dev override (never commit real secrets): create backend/local_settings.py with GROQ_API_KEY = "..."
try:
    if not GROQ_API_KEY:
        from local_settings import GROQ_API_KEY as DEV_KEY  # type: ignore
        GROQ_API_KEY = DEV_KEY
        print("[INFO] Loaded GROQ_API_KEY from local_settings.py (dev)")
except Exception:
    pass

# Plaintext file fallback (backend/groq_key.txt) for convenience (ignored by git via .gitignore)
if not GROQ_API_KEY:
    _groq_key_file = os.path.join(os.path.dirname(__file__), 'groq_key.txt')
    if os.path.isfile(_groq_key_file):
        try:
            with open(_groq_key_file, 'r', encoding='utf-8') as fh:
                candidate = fh.read().strip()
                if candidate:
                    GROQ_API_KEY = candidate
                    print('[INFO] Loaded GROQ_API_KEY from groq_key.txt (DEV USE ONLY)')
        except Exception as _e:
            print(f'[WARN] Failed reading groq_key.txt: {_e}')

# LAST-RESORT (not recommended) hardcoded fallback.
# To use (LOCAL ONLY): replace None with your key string, e.g.
# HARDCODED_DEV_GROQ_KEY = "gsk_...."  # DO NOT COMMIT REAL SECRETS
HARDCODED_DEV_GROQ_KEY = None
if not GROQ_API_KEY and HARDCODED_DEV_GROQ_KEY:
    GROQ_API_KEY = HARDCODED_DEV_GROQ_KEY
    print("[INFO] Using HARDCODED_DEV_GROQ_KEY fallback (development only)")

if not GROQ_API_KEY:
    print("[WARN] GROQ_API_KEY not set (env/.env or local_settings). AI routes will return an error until configured.")

client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL) if GROQ_API_KEY else None

# Debug (non-sensitive) masked print to help user verify key load state
def _debug_key_state():
    masked = None
    if GROQ_API_KEY:
        masked = f"{GROQ_API_KEY[:6]}...{GROQ_API_KEY[-4:]}"
    print(f"[DEBUG] GROQ key loaded: {bool(GROQ_API_KEY)} | masked: {masked}")

_debug_key_state()

# Fail fast with explicit remediation guidance if still missing the key.
if not GROQ_API_KEY:
    # Extra diagnostic: list any env vars that look similar to GROQ_API_KEY
    possible = {
        k: (len(v) if v else 0)
        for k, v in os.environ.items()
        if "GROQ" in k.upper()
    }
    if possible:
        print(f"[DEBUG] Detected GROQ-like environment variables (name -> length): {possible}")
    else:
        print("[DEBUG] No GROQ-like environment variables detected in current process environment.")
    # Show directory listings to confirm .env and key file presence
    try:
        print(
            "[DEBUG] Repo root listing (subset):",
            sorted(os.listdir(os.getcwd()))[:30],
        )
        print(
            "[DEBUG] Backend dir listing (subset):",
            sorted(os.listdir(os.path.dirname(__file__)))[:30],
        )
    except Exception as _ls_err:
        print(f"[DEBUG] Directory listing failed: {_ls_err}")
    missing_msg = (
        "\n[ERROR] GROQ_API_KEY is not configured.\n"
        "Quick ways to fix (choose ONE):\n"
        "  1) Create backend/local_settings.py with: GROQ_API_KEY = 'YOUR_KEY'\n"
        "  2) PowerShell (session only):  $env:GROQ_API_KEY='YOUR_KEY'\n"
        "  3) Create .env (root or backend) line: GROQ_API_KEY=YOUR_KEY\n"
        "  4) Persistent user env (PowerShell): [System.Environment]::SetEnvironmentVariable('GROQ_API_KEY','YOUR_KEY','User')\n"
        "Then restart:  python .\\backend\\app.py\n"
        "If you already did one of these and still see this, verify /debug/config and ensure the file is named .env (not .env.txt)."
    )
    raise SystemExit(missing_msg)

@app.route('/health')
def health():
    """Health/status endpoint to help diagnose configuration issues."""
    return (
        jsonify(
            {
                "status": "ok",
                "has_groq_key": bool(GROQ_API_KEY),
                "model": GROQ_MODEL if GROQ_API_KEY else None,
                "model_fallbacks": GROQ_FALLBACK_MODELS if GROQ_API_KEY else [],
                "spaCy_model_loaded": bool(nlp),
                "max_upload_mb": app.config.get("MAX_CONTENT_LENGTH", 0)
                // (1024 * 1024),
            }
        ),
        200,
    )

@app.route('/debug/config')
def debug_config():
    """Restricted debug info (no full secrets) to help troubleshoot key loading."""
    if os.getenv("APP_ENV", "dev").lower() not in {"dev", "local", "debug"}:
        return (
            jsonify({"error": "Debug endpoint is disabled in non-dev environments."}),
            403,
        )
    masked = None
    if GROQ_API_KEY:
        masked = f"{GROQ_API_KEY[:6]}...{GROQ_API_KEY[-4:]}"
    tried_paths = {
        "cwd": os.getcwd(),
        "backend_dir": os.path.dirname(__file__),
        "root_env_exists": os.path.isfile(os.path.join(os.getcwd(), ".env")),
        "backend_env_exists": os.path.isfile(
            os.path.join(os.path.dirname(__file__), ".env")
        ),
    }
    return (
        jsonify(
            {
                "groq_key_present": bool(GROQ_API_KEY),
                "groq_key_masked": masked,
                "model": GROQ_MODEL,
                "model_fallbacks": GROQ_FALLBACK_MODELS,
                "temperature": GROQ_TEMPERATURE,
                "top_p": GROQ_TOP_P,
                "paths": tried_paths,
                "accepted_aliases": [
                    "GROQ_API_KEY",
                    "GROQ_KEY",
                    "GROQ_APIKEY",
                    "GROQ_SECRET",
                    "GROQ",
                ],
                "python_cwd": os.getcwd(),
            }
        ),
        200,
    )

def _call_groq(prompt: str, max_retries: int = 3) -> str:
    """Send a prompt to Groq using the OpenAI-compatible client and return text.

    Retries on transient HTTP / rate / timeout errors.
    """
    if not client:
        raise RuntimeError("GROQ_API_KEY is not configured on the server.")

    def _is_model_block_error(err: Exception) -> bool:
        msg = str(err)
        return (
            "model_permission_blocked_project" in msg
            or "blocked at the project level" in msg
            or "model_not_found" in msg
        )

    # Build candidate model list (primary first, then fallbacks)
    candidates = [GROQ_MODEL] + [m for m in GROQ_FALLBACK_MODELS if m != GROQ_MODEL]
    last_err = None

    for model in candidates:
        for attempt in range(1, max_retries + 1):
            try:
                # Using responses endpoint (Groq supports OpenAI responses API)
                resp = client.responses.create(
                    model=model,
                    input=prompt,
                    max_output_tokens=2048,
                    temperature=GROQ_TEMPERATURE,
                    top_p=GROQ_TOP_P,
                )
                return resp.output_text.strip()
            except Exception as e:  # Broad catch to simplify; could refine (RateLimitError, etc.)
                last_err = e
                # If model is blocked, immediately try next model
                if _is_model_block_error(e):
                    break
                if attempt == max_retries:
                    break

    raise RuntimeError(
        f"Groq AI request failed after {max_retries} attempts across models {candidates}: {last_err}"
    )

def extract_resume_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_text(file_path)
    elif ext == '.docx':
        doc = Document(file_path)
        return '\n'.join([p.text for p in doc.paragraphs])
    else:
        return ''

# -------------------------------------------------------------
# Parsing helpers for AI response (robust against minor variation)
# -------------------------------------------------------------
SECTION_PATTERNS = {
    "rating": re.compile(
        r"^\s*Rating\s*[:\-]?\s*(\d{1,2})\b", re.IGNORECASE | re.MULTILINE
    ),
    "keyword_gaps": re.compile(
        r"^\s*Keyword\s+Gaps\s*\([^)]*\)?\s*[:\-]?\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "improved_summary": re.compile(
        (
            r"^\s*Improved\s+Summary[^:]*:\s*(.+?)"
            r"(?=^\s*Improved\s+Bullet|^\s*Priority\s+Fix|^\s*Suggestions|^\s*Keyword\s+Gaps|\Z)"
        ),
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    ),
    "improved_bullets": re.compile(
        (
            r"^\s*Improved\s+Bullet\s+Examples\s*:?\s*(.+?)"
            r"(?=^\s*Priority\s+Fix|^\s*Improved\s+Summary|^\s*Suggestions|^\s*Keyword\s+Gaps|\Z)"
        ),
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    ),
    "priority_fixes": re.compile(
        (
            r"^\s*Priority\s+Fix\s+Order\s*:?\s*(.+?)"
            r"(?=^\s*Improved\s+Bullet|^\s*Improved\s+Summary|^\s*Suggestions|^\s*Keyword\s+Gaps|\Z)"
        ),
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    ),
    "suggestions_block": re.compile(
        (
            r"^\s*Suggestions\s*:?\s*(.+?)"
            r"(?=^\s*Keyword\s+Gaps|^\s*Improved\s+Summary|^\s*Improved\s+Bullet|^\s*Priority\s+Fix|\Z)"
        ),
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    ),
}

def _clean_section(text: str | None) -> str | None:
    if not text:
        return None
    # Strip leading/trailing whitespace and extraneous blank lines
    cleaned = text.strip()
    # Collapse >2 blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned if cleaned else None

def parse_ai_analysis(ai_text: str) -> dict:
    """Parse the AI reply into structured sections.

    Returns dict with keys: rating, suggestions, keyword_gaps, improved_summary,
    improved_bullets, priority_fixes. Missing sections will be None.
    """
    result: dict[str, str | None] = {
        "rating": None,
        "suggestions": None,
        "keyword_gaps": None,
        "improved_summary": None,
        "improved_bullets": None,
        "priority_fixes": None,
    }

    # Rating (single number)
    m = SECTION_PATTERNS["rating"].search(ai_text)
    if m:
        result["rating"] = m.group(1)

    # Suggestions block
    m = SECTION_PATTERNS["suggestions_block"].search(ai_text)
    if m:
        result["suggestions"] = _clean_section(m.group(1))

    # Keyword gaps (comma separated line)
    m = SECTION_PATTERNS["keyword_gaps"].search(ai_text)
    if m:
        kg = m.group(1).strip()
        # Normalize spacing after commas
        kg = re.sub(r'\s*,\s*', ', ', kg)
        result["keyword_gaps"] = kg

    # Improved Summary
    m = SECTION_PATTERNS["improved_summary"].search(ai_text)
    if m:
        result["improved_summary"] = _clean_section(m.group(1))

    # Improved Bullet Examples
    m = SECTION_PATTERNS["improved_bullets"].search(ai_text)
    if m:
        result["improved_bullets"] = _clean_section(m.group(1))

    # Priority Fix Order
    m = SECTION_PATTERNS["priority_fixes"].search(ai_text)
    if m:
        # Keep enumerated lines only (1.,2., bullet dashes)
        block = _clean_section(m.group(1))
        if block:
            # Trim any trailing unrelated text (heuristic) nothing for now
            result["priority_fixes"] = block

    return result


@app.route('/upload', methods=['POST'])
# Endpoint to handle resume uploads
def upload_resume():
    """Handle a resume upload, extract text, and return structured AI analysis.

    Improvements:
    - Ensures temp directory exists (fixes FileNotFoundError for temp\\<file>)
    - Sanitizes filename
    - Validates extensions (.pdf, .docx)
    - Cleans up temp file in finally block
    - Provides clearer error messages
    """
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    allowed_ext = {".pdf", ".docx"}
    allowed_mime = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return (
            jsonify({"error": f"Unsupported file type {ext}. Allowed: PDF, DOCX"}),
            400,
        )

    if file.mimetype and file.mimetype not in allowed_mime:
        return jsonify({"error": f"Unsupported MIME type {file.mimetype}."}), 400

    safe_name = secure_filename(file.filename)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, safe_name)

    try:
        file.save(temp_path)
        resume_text = extract_resume_text(temp_path)
        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from resume."}), 400

        if not client:
            return (
                jsonify(
                    {
                        "error": "GROQ_API_KEY not configured on server. Set it in environment or .env to enable analysis."
                    }
                ),
                500,
            )

        prompt = (
            "You are a senior technical resume optimization expert. "
            "Provide a rigorous, detailed analysis with actionable, specific improvements. "
            "Use strong, metric-focused rewrites. Avoid generic advice. Do NOT invent experience; only reshape what's implied. "
            "Return content in exactly these sections (no extra text before or after):\n"
            "Rating: <1-10 overall score>\n"
            "Suggestions:\n"
            "- <High-impact item 1 with concrete example / rewrite>\n"
            "- <High-impact item 2 ...> (5–12 bullets total, prioritize quantified impact, clarity, ATS alignment)\n"
            "Keyword Gaps (comma-separated): <missing or weak keywords>\n"
            "Improved Summary (10/10):\n<rewritten professional summary>\n"
            "Improved Bullet Examples:\n"
            "<2-4 transformed bullet rewrites showing before -> after OR just the improved versions>\n"
            "Priority Fix Order:\n1. <Most critical fix>\n2. <Second>\n3. <Third> (limit to top 5)\n"
            f"\nResume:\n{resume_text}\n"
            "Ensure each bullet is specific, includes measurable impact where possible "
            "(%, time saved, scale, users, revenue, performance changes)."
        )
        ai_reply = _call_groq(prompt)
        parsed = parse_ai_analysis(ai_reply)

        # Determine completeness: require at minimum rating + suggestions + at least one of summary/bullets
        if not (
            parsed["rating"]
            and parsed["suggestions"]
            and (parsed["improved_summary"] or parsed["improved_bullets"])
        ):
            return (
                jsonify(
                    {
                        "error": "AI could not provide a complete analysis. Please try again.",
                        "raw_ai_output": ai_reply,
                        "parsed_partial": parsed,
                    }
                ),
                500,
            )

        # Backwards compatibility fields expected by current frontend (ai_example previously)
        legacy_example = parsed["improved_bullets"] or parsed["improved_summary"]

        return jsonify(
            {
                "ai_rating": parsed["rating"],
                "ai_suggestions": parsed["suggestions"],
                "ai_example": legacy_example,
                "keyword_gaps": parsed["keyword_gaps"],
                "improved_summary": parsed["improved_summary"],
                "improved_bullet_examples": parsed["improved_bullets"],
                "priority_fix_order": parsed["priority_fixes"],
                "raw_ai_output": ai_reply,
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    data = request.get_json()
    resume_text = data.get('resume_text', '')
    if not resume_text:
        return jsonify({'error': 'No resume text provided'}), 400

    prompt = (
        "You are an expert resume coach. Provide concise, actionable improvement suggestions (bullet list) and then a polished summary rewrite.\n" \
        f"Resume text:\n{resume_text}"
    )
    try:
        ai_reply = _call_groq(prompt)
        return jsonify({'ai_suggestions': ai_reply, 'model': GROQ_MODEL})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

if __name__ == '__main__':
    # Run the Flask application in debug mode
    app.run(debug=True)