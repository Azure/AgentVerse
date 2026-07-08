# FoundryAirlines demo — single image: FastAPI serves the UI (at /) and the API.
# Build context is this folder (src/foundryairlines-demo).
#   docker build -t <acr>/foundryairlines-demo-web:latest .
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

# Seed the local bookings SQLite DB used by the flights agent (idempotent).
RUN python -m app.backend.seed_db || true

EXPOSE 8765
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8765"]
