# Free Hosting

## Option A — Render (free tier)

1. Push repo to GitHub.
2. Create a Web Service on Render.
3. Build command:

```bash
    pip install -r backend/requirements.txt
    python -m spacy download en_core_web_sm
```

Start command:

```bash
    python backend/app.py
```

Add env var GROQ_API_KEY.

## Option B — Fly.io (free tier allowance)

If you want, I can add a Procfile or update Dockerfile for a one-click deploy.

```bash
    npm i -g flyctl
    flyctl auth login
    flyctl launch --now
    flyctl secrets set GROQ_API_KEY=your_key
```
