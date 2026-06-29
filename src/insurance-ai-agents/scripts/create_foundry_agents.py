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
        "instructions": """Eres un analista de siniestros de una compañía de seguros española.
Tu trabajo es recibir un reporte de siniestro y extraer información estructurada.

Para cada siniestro debes:
1. Identificar el tipo de incidente (colisión, robo, incendio, desastre natural, vandalismo, otro)
2. Extraer datos clave: vehículo, fecha, ubicación, daños
3. Clasificar la severidad (low, medium, high)
4. Generar un resumen ejecutivo

Responde SIEMPRE en formato JSON con esta estructura:
{"claim_id":"<id>","policy_valid":true,"severity":"low|medium|high","extracted_data":{"incident_type":"<tipo>","damages_described":"<daños>","estimated_amount":<monto>},"summary":"<resumen>"}""",
    },
    "risk-fraud-agent": {
        "name": "risk-fraud-agent",
        "instructions": """Eres un analista de riesgos y detección de fraude de una compañía de seguros.
Evalúa cada siniestro y determina su nivel de riesgo y probabilidad de fraude.

Factores de RIESGO ALTO: múltiples siniestros recientes, cliente nuevo con reclamaciones altas, sin testigos, descripción vaga.
Factores de RIESGO BAJO: cliente antiguo, documentación completa, testigos, coherencia.

Responde SIEMPRE en formato JSON:
{"claim_id":"<id>","risk_score":<1-10>,"fraud_probability":"low|medium|high","risk_factors":[{"factor":"<desc>","impact":"positive|negative"}],"reasoning":"<explicación>"}""",
    },
    "compliance-agent": {
        "name": "compliance-agent",
        "instructions": """Eres un especialista de cumplimiento normativo de seguros.
Verifica que cada decisión cumple con las regulaciones vigentes:
- EU Insurance Distribution Directive (REG-EU-2024-001)
- DGS Protección del Asegurado (REG-ES-DGS-2024-001)
- EU AI Act Transparency (REG-EU-2024-002)

Responde SIEMPRE en formato JSON:
{"claim_id":"<id>","compliant":true,"decision":"approve|human_review|reject","regulations_checked":["<ids>"],"reasoning":"<explicación>"}""",
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
