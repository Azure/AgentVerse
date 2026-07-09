# Production Scheduling AI Agents — container image for Azure Container Apps.
# Built in the cloud with `az acr build` (no local Docker needed); Terraform
# triggers the build automatically when source files change (see infra/main.tf).

FROM python:3.12-slim

WORKDIR /app

# Dependencies first so code-only changes reuse this cached layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Same entrypoint as the App Service path and local runs.
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
