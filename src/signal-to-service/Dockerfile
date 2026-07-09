# Signal-to-Service demo — single image: FastAPI serves the UI (at /) and the SSE API.
# Build context is this folder (src/signal-to-service).
#   docker build -t <acr>/signal-to-service-web:latest .
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

EXPOSE 8767
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8767"]
