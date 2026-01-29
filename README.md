# Resume Analyzer & Builder

[![CI](https://img.shields.io/github/actions/workflow/status/SagarBiswas-MultiHAT/resume-analyzer-builder/ci.yml)](https://github.com/SagarBiswas-MultiHAT/resume-analyzer-builder/actions)
[![License](https://img.shields.io/github/license/SagarBiswas-MultiHAT/resume-analyzer-builder)](LICENSE)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-brightgreen)](https://github.com/SagarBiswas-MultiHAT/resume-analyzer-builder/security/dependabot)

A local-first Flask web app that accepts PDF/DOCX resumes, extracts text, calls a Groq/OpenAI-compatible model, and returns structured, actionable improvements with ratings, keyword gaps, and rewrite examples.

## Table of contents

- Overview
- Features
- How it works
- Tech stack
- Project structure
- Quickstart
- Configuration
- Usage (UI + API)
- Output fields
- Data flow and limits
- Troubleshooting
- Development
- Docker
- Security
- Contributing
- License

## Overview

Resume Analyzer & Builder is a single-page app for fast, clear resume feedback. You upload a resume, the backend extracts text and requests a structured critique from an LLM, and the UI renders a rating, prioritized fixes, keyword gaps, and improved examples you can copy or download.

It is designed to be simple to run locally, easy to understand, and focused on actionable improvements rather than generic advice.

![App screenshot](https://imgur.com/1reTyVi.png)

![App screenshot 2](https://imgur.com/UuN1BO9.png)

## Features

- Upload PDF/DOCX resumes (max 5 MB).
- Local text extraction using pdfminer (PDF) and python-docx (DOCX).
- Groq OpenAI-compatible client with retry + model fallbacks.
- Structured analysis with rating, suggestions, keyword gaps, improved summary, improved bullets, and priority fix order.
- Modern UI with drag-and-drop, dark mode, copy buttons, and a downloadable text report.
- Safety defaults: localhost-only CORS and automatic temp file cleanup.
- Helpful health/debug endpoints for local troubleshooting.

## How it works

1. The browser uploads a resume to /upload.
2. Flask stores the file in a temporary directory and extracts text.
3. The extracted text is sent to Groq via the OpenAI-compatible Responses API.
4. The response is parsed into named sections.
5. The UI renders the structured results and enables copy/download actions.

## Tech stack

- Backend: Flask, pdfminer.six, python-docx, spaCy, python-dotenv
- AI client: Groq OpenAI-compatible SDK
- Frontend: vanilla HTML/CSS/JS

## Project structure

- [backend/app.py](backend/app.py): Flask server, AI call, parsing, and endpoints
- [backend/requirements.txt](backend/requirements.txt): backend dependencies
- [frontend/index.html](frontend/index.html): single-page UI
- [frontend/script.js](frontend/script.js): upload, render, copy, download
- [frontend/styles.css](frontend/styles.css): styles and theming
- [tests/test_parsing.py](tests/test_parsing.py): parser tests

## Key points

- Backend: `backend/app.py` (Flask)
- Frontend: `frontend/` (static assets served by Flask)
- AI: OpenAI-compatible Groq client (requires `GROQ_API_KEY`)
- Upload limits: 5 MB; allowed types: PDF, DOCX

## Quickstart

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
```

Run the app:

```powershell
python .\backend\app.py
```

Open http://localhost:5000.

## Configuration

Create a .env file in the repo root or backend/ (both are supported).

Required:

```text
GROQ_API_KEY=your_groq_api_key_here
```

Optional (defaults shown):

```text
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODELS=llama-3.1-70b-versatile,llama-3.1-8b-instant,mixtral-8x7b-32768
GROQ_TEMPERATURE=0.2
GROQ_TOP_P=0.9
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
APP_ENV=dev
```

Notes:

- If GROQ_API_KEY is missing, the server exits with a clear error message.
- For local dev, backend/local_settings.py or backend/groq_key.txt can also provide the key.

## Usage

### UI

1. Open the app in a browser.
2. Drag & drop a PDF/DOCX or click to select one.
3. Click Upload Resume.
4. Review the rating, suggestions, keyword gaps, and rewrite examples.
5. Copy blocks or download the analysis as resume_analysis.txt.

### API

Base URL: http://localhost:5000

- GET /health
- GET /debug/config (dev-only)
- POST /upload (multipart form with resume file)
- POST /analyze (JSON with resume_text)

Example (PowerShell upload):

```powershell
Invoke-RestMethod -Uri http://localhost:5000/upload -Method Post -Form @{ resume = Get-Item .\sample.pdf }
```

Example (curl analyze):

```bash
curl -X POST http://localhost:5000/analyze \
	-H "Content-Type: application/json" \
	-d '{"resume_text":"Your resume text here"}'
```

## Output fields

The /upload endpoint returns:

- ai_rating: overall score (1–10)
- ai_suggestions: detailed bullet list
- keyword_gaps: comma-separated missing keywords
- improved_summary: rewritten summary
- improved_bullet_examples: improved bullet rewrites
- priority_fix_order: ranked list of the top fixes
- raw_ai_output: full model response (for debugging)

## Data flow and limits

- Upload limit: 5 MB (server-side enforced).
- Supported formats: .pdf and .docx only.
- Temporary files are removed after processing.
- CORS is restricted to localhost by default.
- The /debug/config endpoint is only enabled when APP_ENV is dev/local/debug.

## Troubleshooting

- GROQ_API_KEY missing: add it to .env, backend/local_settings.py, or a session env var.
- spaCy model not found: run python -m spacy download en_core_web_sm.
- Model blocked: set GROQ_MODEL or GROQ_FALLBACK_MODELS to a permitted model.
- Empty extraction: ensure the PDF/DOCX is text-based (scanned PDFs may be empty).
- Debug info: visit /health or /debug/config (APP_ENV=dev).

## Development

```powershell
python -m pytest -q
pre-commit run --all-files
```

## Docker

```powershell
docker build -t resume-analyzer-builder:local .
docker run -p 5000:5000 -e GROQ_API_KEY=your_key resume-analyzer-builder:local
```

## Security

- Do not commit API keys. Use environment variables or local-only files.
- Uploaded files are stored in a temp directory and deleted after processing.
- CORS is locked to localhost by default.

See SECURITY.md for reporting.

## Contributing

See CONTRIBUTING.md and CODE_OF_CONDUCT.md.

## License

MIT. See LICENSE.

## Explain this project in 60 seconds

This is a local Flask web app that reads PDF/DOCX resumes, extracts text, and asks a Groq/OpenAI-compatible model for a structured critique. The response is parsed into a rating, suggestions, keyword gaps, improved summary, and bullet examples, then rendered in a clean UI with copy/download helpers. It is built to be simple to run, clear to read, and focused on actionable resume improvements.
