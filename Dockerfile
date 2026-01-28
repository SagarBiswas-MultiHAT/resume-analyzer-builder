FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/ backend/
COPY frontend/ frontend/
COPY requirements-dev.txt requirements-dev.txt
COPY backend/requirements.txt backend/requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install -r backend/requirements.txt \
    && python -m spacy download en_core_web_sm

EXPOSE 5000

CMD ["python", "backend/app.py"]
