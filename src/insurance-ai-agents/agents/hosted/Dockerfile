# Foundry hosted agent — insurance claims orchestrator (invocations protocol, port 8088).
#
# The build CONTEXT must be the REPO ROOT: this image copies the whole agents/ tree, and
# agents/orchestrator/agent.py imports the per-agent modules (claims-intake, risk-assessment,
# compliance) and agents/shared.
#
# Cloud build (no local Docker required):
#   az acr build --registry insaidemoacrjii435hjlwyyc \
#     --image insurance-claims-orchestrator:<timestamp> \
#     --platform linux/amd64 --source-acr-auth-id "[caller]" \
#     --file agents/hosted/Dockerfile .
#
# Hosted agents run on Linux/amd64 — always build for that platform.

FROM python:3.12-slim AS base
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8088

COPY agents/hosted/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Full agents/ package tree (orchestrator + per-agent modules + shared helpers).
COPY agents/ /app/agents/

EXPOSE 8088
CMD ["python", "agents/hosted/app.py"]
