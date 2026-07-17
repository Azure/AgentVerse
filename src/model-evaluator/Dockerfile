# Model Evaluator — single image: FastAPI serves the UI (at /) and the JSON/SSE API.
# Build context is this folder (src/model-evaluator).
#   docker build -t <acr>/model-evaluator-web:latest .
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

EXPOSE 8770
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8770"]
