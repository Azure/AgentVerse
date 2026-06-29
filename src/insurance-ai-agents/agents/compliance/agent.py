"""Compliance Agent - Validates claims against current regulations and business rules."""

import json
import os
import logging

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

from agents.shared.azure_client import get_openai_client

from agents.compliance.rules import evaluate_compliance, get_applicable_regulations, RULES

load_dotenv(override=False)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un especialista de cumplimiento normativo de una compañía de seguros española.
Tu trabajo es verificar que cada decisión sobre siniestros cumple con las regulaciones vigentes
y las políticas internas de la compañía.

Para cada siniestro debes:
1. Verificar las regulaciones aplicables
2. Validar contra los umbrales regulatorios actuales
3. Determinar si la reclamación puede ser aprobada automáticamente, necesita revisión humana, o debe rechazarse
4. Documentar todos los controles realizados (esto es OBLIGATORIO por la normativa EU AI Act)

IMPORTANTE: Responde SIEMPRE en formato JSON con esta estructura:
{
    "claim_id": "<id>",
    "compliant": true/false,
    "decision": "approve|human_review|reject",
    "regulations_checked": ["<reg_ids>"],
    "rules_applied": {<reglas aplicadas y sus valores>},
    "reasoning": "<explicación completa de la validación>"
}"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_regulations",
            "description": "Obtiene la lista de regulaciones aplicables según el monto y riesgo del siniestro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_amount": {"type": "number", "description": "Monto del siniestro en euros"},
                    "risk_score": {"type": "number", "description": "Score de riesgo (1-10)"},
                },
                "required": ["claim_amount", "risk_score"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_thresholds",
            "description": "Valida el siniestro contra los umbrales regulatorios y reglas de negocio actuales.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_amount": {"type": "number", "description": "Monto del siniestro en euros"},
                    "risk_score": {"type": "number", "description": "Score de riesgo (1-10)"},
                    "fraud_probability": {"type": "string", "description": "Probabilidad de fraude: low, medium, high"},
                },
                "required": ["claim_amount", "risk_score", "fraud_probability"],
            },
        },
    },
]


def _check_regulations(claim_amount: float, risk_score: float) -> dict:
    regs = get_applicable_regulations(claim_amount, risk_score)
    return {
        "applicable_regulations": regs,
        "current_rules": RULES,
    }


def _validate_thresholds(claim_amount: float, risk_score: float, fraud_probability: str) -> dict:
    return evaluate_compliance(claim_amount, risk_score, fraud_probability)


TOOL_MAP = {
    "check_regulations": _check_regulations,
    "validate_thresholds": _validate_thresholds,
}


async def run(claim_input: dict, intake_result: dict, risk_result: dict) -> dict:
    """Run the Compliance Agent.
    
    Args:
        claim_input: Original claim input
        intake_result: Result from Claims Intake Agent
        risk_result: Result from Risk & Fraud Agent
    Returns:
        Dict with compliance validation result
    """
    client = await get_openai_client()

    risk_score = risk_result.get("risk_score", 5)
    fraud_prob = risk_result.get("fraud_probability", "medium")
    amount = claim_input.get("estimated_amount", 0)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Valida el cumplimiento normativo del siguiente siniestro:\n\n"
                f"ID Siniestro: {claim_input.get('claim_id', 'CLM-UNKNOWN')}\n"
                f"Monto estimado: {amount}€\n"
                f"Risk score: {risk_score}/10\n"
                f"Probabilidad de fraude: {fraud_prob}\n\n"
                f"Resultado de intake:\n{json.dumps(intake_result, indent=2, ensure_ascii=False)}\n\n"
                f"Resultado de evaluación de riesgo:\n{json.dumps(risk_result, indent=2, ensure_ascii=False)}\n\n"
                f"Por favor:\n"
                f"1. Verifica las regulaciones aplicables para un siniestro de {amount}€ con risk score {risk_score}\n"
                f"2. Valida contra los umbrales regulatorios actuales\n"
                f"3. Proporciona tu decisión de compliance"
            ),
        },
    ]

    for _ in range(2):
        response = await client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini"),
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            reasoning_effort=os.environ.get("OPENAI_REASONING_EFFORT", "low"),
        )

        msg = response.choices[0].message
        if not msg.tool_calls:
            break

        messages.append(msg)
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            result = TOOL_MAP[fn_name](**fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    if msg.tool_calls:
        response = await client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini"),
            messages=messages,
            reasoning_effort=os.environ.get("OPENAI_REASONING_EFFORT", "low"),
        )

    content = response.choices[0].message.content
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return {
            "claim_id": claim_input.get("claim_id", "CLM-UNKNOWN"),
            "compliant": True,
            "decision": "human_review",
            "regulations_checked": [],
            "reasoning": content,
        }
