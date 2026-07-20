# Azure SRE Agent demo — single image: FastAPI serves the UI (at /) and the JSON API.
# Build context is this folder (src/sre-agent-demo).
#   docker build -t <acr>/sre-agent-demo-web:latest .
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

EXPOSE 8780
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8780"]
