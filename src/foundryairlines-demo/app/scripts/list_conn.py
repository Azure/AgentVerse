import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv("app/.env")
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
proj = AIProjectClient(endpoint=os.getenv("PROJECT_ENDPOINT"), credential=DefaultAzureCredential())
for c in proj.connections.list():
    print(c.name, "|", c.type, "|", c.id)
