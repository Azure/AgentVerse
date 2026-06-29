################################################################################
# Insurance AI Demo - Backend image
#
# Build CONTEXT is the repo root (not /backend) because main.py imports
# `agents.*` from one level up via:
#     sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# so the runtime layout has to be:
#     /app
#       /agents/...   (sibling of backend)
#       /backend/main.py
#
# Build & push from the repo root:
#     docker build -t <acr>/insurance-ai-backend:latest -f backend/Dockerfile .
################################################################################
FROM python:3.12-slim AS base
WORKDIR /app

# Install backend + agent dependencies in one layer. Backend's requirements.txt
# already pins agent-framework, azure-cosmos, PyJWT etc., and is a strict
# superset of agents/requirements.txt — installing it covers both.
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# Copy source. Order: agents first (rarely change in deploys driven by
# dashboard tweaks), then backend (changes most often).
COPY agents/  /app/agents/
COPY backend/ /app/backend/

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
