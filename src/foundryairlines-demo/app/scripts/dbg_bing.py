import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.backend.agents import _ensure_clients, MODEL_DEPLOYMENT_NAME
import app.backend.agents as A
A._ensure_clients()
client = A._agents_client
print("bing conn id:", A._bing_conn_id)
from azure.ai.agents.models import BingGroundingTool
bing = BingGroundingTool(connection_id=A._bing_conn_id)
print("defs:", bing.definitions)
agent = client.create_agent(
    model=MODEL_DEPLOYMENT_NAME,
    name="dbg-bing",
    instructions='Use Bing search. Return ONLY a JSON object {"title":..., "short_description":...}',
    tools=bing.definitions,
)
print("agent:", agent.id)
th = client.threads.create()
client.messages.create(thread_id=th.id, role="user",
    content="Find one notable event in Berlin, Germany on 2026-05-19. Return ONLY a JSON object with title and short_description.")
run = client.runs.create_and_process(thread_id=th.id, agent_id=agent.id)
print("status:", run.status, "err:", getattr(run, "last_error", None))
msgs = list(client.messages.list(thread_id=th.id))
for m in msgs:
    print("---", m.role)
    for c in m.content:
        print(c)
client.delete_agent(agent.id)
