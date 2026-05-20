FROM python:3.12-slim

WORKDIR /app

COPY hostedagent/requirements-hosted.txt .
RUN pip install --no-cache-dir -r requirements-hosted.txt

COPY agentverse ./agentverse
COPY hostedagent/hosted_workflow.py ./hostedagent/hosted_workflow.py
COPY hostedagent/__init__.py ./hostedagent/__init__.py
COPY data ./data

ENV AGENTVERSE_USE_DEFAULT_AZURE_CREDENTIAL=1
EXPOSE 8088

CMD ["python", "-m", "hostedagent.hosted_workflow"]
