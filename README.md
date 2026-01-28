# Resume Analyzer & Builder

[![CI](https://img.shields.io/github/actions/workflow/status/your-org/Resume-Analyzer-Builder/ci.yml)](https://github.com/your-org/Resume-Analyzer-Builder/actions)
[![License](https://img.shields.io/github/license/your-org/Resume-Analyzer-Builder)](LICENSE)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-brightgreen)](https://github.com/your-org/Resume-Analyzer-Builder/security/dependabot)

A local Flask web app that accepts PDF/DOCX resumes, extracts text, calls a Groq/OpenAI-compatible model, and returns structured, actionable improvements.

## 60-second elevator pitch

Resume Analyzer & Builder helps you quickly improve resumes by extracting content from PDF/DOCX files and generating targeted, metric-focused rewrites. It provides a clear AI rating, prioritized fixes, and example bullet improvements, all through a simple single-page UI.

![](https://imgur.com/1reTyVi.png)

---

![](https://imgur.com/UuN1BO9.png)

## Key points

- Backend: `backend/app.py` (Flask)
- Frontend: `frontend/` (static assets served by Flask)
- AI: OpenAI-compatible Groq client (requires `GROQ_API_KEY`)
- Upload limits: 5 MB; allowed types: PDF, DOCX

## Quickstart (Windows PowerShell)

```powershell
py -3.11 -m venv .venv

win -> .\.venv\Scripts\Activate.ps1
linux -> \.\.venv\Scripts\Activate.ps1

pip install -r backend\requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
```

Create a `.env` file (repo root or backend) and add:

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_TEMPERATURE=0.2
GROQ_TOP_P=0.9
```

Run:

```powershell
python .\backend\app.py
```

Open http://localhost:5000.

## API

Base URL: http://localhost:5000

- GET `/health`
- GET `/debug/config` (dev only)
- POST `/upload` (PDF/DOCX)
- POST `/analyze` (plain text)

## Examples

Upload a file with PowerShell:

```powershell
Invoke-RestMethod -Uri http://localhost:5000/upload -Method Post -Form @{ resume = Get-Item .\sample.pdf }
```

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

Do not commit API keys. Use environment variables or local-only files. See SECURITY.md for reporting.

## Contributing

See CONTRIBUTING.md and CODE_OF_CONDUCT.md.

## License

MIT. See LICENSE.

## Explain this project in 60 seconds

This project is a local Flask web app that reads PDF/DOCX resumes, extracts text, and sends it to a Groq/OpenAI-compatible model. The response is parsed into a rating, suggestions, keyword gaps, improved summary, and bullet examples, which the frontend renders in a clean UI. It’s ideal for quick resume feedback without a complex setup.
