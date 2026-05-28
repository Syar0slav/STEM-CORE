FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/ ./frontend/
COPY moodle/ ./moodle/
# Сиди (запуск у контейнері: python /seed_….py; DATABASE_URL з docker-compose)
COPY scripts/seed_demo_1000.py /seed_demo_1000.py
COPY scripts/seed_zosh201_dashboard_preview.py /seed_zosh201_dashboard_preview.py

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
