# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    VOICE_NAME=en_US-lessac-medium \
    VOICES_DIR=/voices

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi "uvicorn[standard]" piper-tts pathvalidate \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /voices \
    && chown -R app:app /app /voices

COPY main.py /app/main.py

USER app:app

VOLUME ["/voices"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
