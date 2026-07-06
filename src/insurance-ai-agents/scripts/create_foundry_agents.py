"""Create Foundry prompt agents for the Insurance Claims demo.

Creates 3 specialized agents in Azure AI Foundry:
- Claims Intake Agent
- Risk & Fraud Assessment Agent  
- Compliance Agent

These agents run on Azure AI Agent Service with GPT-5.4-mini.
"""

import os, sys, json
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    FunctionTool,
    ToolSet,
)

ENDPOINT = "https://ins-ai-demo-ais-jii435hjlwyyc.cognitiveservices.azure.com/"
MODEL = "gpt-5.4-mini"

# ── Agent definitions ──

AGENTS = {
    "claims-intake-agent": {
        "name": "claims-intake-agent",
        "instructions": """You are a claims analyst at an insurance company.
Your job is to receive a claim report and extract structured information.

For each claim you must:
1. Identify the incident type (collision, theft, fire, natural disaster, vandalism, other)
2. Extract key data: vehicle, date, location, damages
3. Classify the severity (low, medium, high)
4. Generate an executive summary

ALWAYS respond in JSON format with this structure:
{"claim_id":"<id>","policy_valid":true,"severity":"low|medium|high","extracted_data":{"incident_type":"<type>","damages_described":"<damages>","estimated_amount":<amount>},"summary":"<summary>"}""",
    },
    "risk-fraud-agent": {
        "name": "risk-fraud-agent",
        "instructions": """You are a risk and fraud detection analyst at an insurance company.
Assess each claim and determine its risk level and fraud probability.

HIGH RISK factors: multiple recent claims, new customer with high claims, no witnesses, vague description.
LOW RISK factors: long-standing customer, complete documentation, witnesses, consistency.

ALWAYS respond in JSON format:
{"claim_id":"<id>","risk_score":<1-10>,"fraud_probability":"low|medium|high","risk_factors":[{"factor":"<desc>","impact":"positive|negative"}],"reasoning":"<explanation>"}""",
    },
    "compliance-agent": {
        "name": "compliance-agent",
        "instructions": """You are an insurance regulatory compliance specialist.
Verify that each decision complies with the applicable regulations:
- EU Insurance Distribution Directive (REG-EU-2024-001)
- DGS Policyholder Protection (REG-ES-DGS-2024-001)
- EU AI Act Transparency (REG-EU-2024-002)

ALWAYS respond in JSON format:
{"claim_id":"<id>","compliant":true,"decision":"approve|human_review|reject","regulations_checked":["<ids>"],"reasoning":"<explanation>"}""",
    },
}


def main():
    credential = DefaultAzureCredential()
    client = AgentsClient(endpoint=ENDPOINT, credential=credential)

    created = {}
    for key, agent_def in AGENTS.items():
        print(f"Creating agent: {agent_def['name']}...")
        try:
            agent = client.create_agent(
                model=MODEL,
                name=agent_def["name"],
                instructions=agent_def["instructions"],
            )
            print(f"  ✅ Created: {agent.id}")
            created[key] = agent.id
        except Exception as e:
            print(f"  ❌ Error: {e}")
            # Try to find existing agent
            try:
                agents_list = client.list_agents()
                for a in agents_list:
                    if a.name == agent_def["name"]:
                        print(f"  ♻️  Found existing: {a.id}")
                        created[key] = a.id
                        break
            except Exception:
                pass

    # Save agent IDs for the backend
    config = {
        "endpoint": ENDPOINT,
        "model": MODEL,
        "agents": created,
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "agents", "foundry_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n📋 Agent IDs saved to agents/foundry_config.json")
    print(f"   Endpoint: {ENDPOINT}")
    for k, v in created.items():
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
