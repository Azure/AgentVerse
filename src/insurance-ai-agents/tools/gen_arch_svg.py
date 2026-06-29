"""Generate the architecture SVG diagrams in both Spanish and English.

Both share the same layout, gradients, icons and arrow routing. Only the text
strings change. The brand mark is an inline SVG hexagon so the diagram is
self-contained (no external image dependencies).

Run from repo root:  python tools\\gen_arch_svg.py
Outputs:             images/architecture.svg     (Spanish, default for the demo)
                     images/architecture-en.svg  (English, reference architecture)
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Brand tokens — edit these to rebrand the architecture diagram.
BRAND_NAME = "Helix Insurance"
BRAND_MARK_LETTER = "H"
BRAND_PRIMARY = "#2563EB"   # main brand color (blue-600), replaces former {BRAND_PRIMARY}
BRAND_PRIMARY_DARK = "#1E40AF"   # dark brand color (blue-800), replaces former {BRAND_PRIMARY_DARK}

# ----------------------------------------------------------------------------
# Translatable strings.  Product names ("Microsoft Entra ID", "Azure Container
# Apps", etc.), code identifiers and standard tech acronyms (JWT, OIDC, MSAL,
# WebSocket, HTTPS, MI, etc.) stay in their canonical English form in both
# languages.
# ----------------------------------------------------------------------------
STRINGS = {
    "es": {
        "title_attr": "Insurance AI Agents — Arquitectura de Referencia",
        "desc_attr": (
            "Demo de procesamiento multi-agente de siniestros: dashboard React, "
            "backend FastAPI sobre Azure Container Apps, Microsoft Agent Framework "
            "orquestando los agentes Intake / Risk / Compliance, Azure OpenAI a "
            "través del APIM AI Gateway, Cosmos DB y Blob Storage para estado, "
            "Microsoft Entra ID para identidad, Application Insights para "
            "observabilidad, GitHub Enterprise (CODEOWNERS, Eval Gate, Actions) "
            "para gobernanza."
        ),
        "aria_label": "Arquitectura de referencia de Insurance AI Agents",
        "subtitle": (
            "GESTIÓN DE SINIESTROS MULTI-AGENTE GOBERNADA · ARQUITECTURA DE REFERENCIA"
        ),
        "zone_edge": "BORDE · CAPA CLIENTE",
        "zone_azure": "MICROSOFT AZURE · TENANT EMPRESARIAL",
        "zone_governance": (
            "GITHUB ENTERPRISE · CAPA DE GOBERNANZA  "
            "(PROTEGE Y AUDITA TODO LO DE ARRIBA)"
        ),
        "users_header": "USUARIOS FINALES · NAVEGADOR",
        "user_customer": "Cliente",
        "user_operator": "Operario",
        "role_customer": "rol: Customer.Submit",
        "role_operator": "rol: Operator.Review",
        "dashboard_bullet_1": "▸ Vistas por rol",
        "dashboard_bullet_2": "▸ Cliente · Operario · Riesgo",
        "dashboard_bullet_3": "▸ Compliance · Demo automática",
        "dashboard_bullet_4": "▸ Streaming WebSocket en vivo",
        "legend_title": "LEYENDA",
        "legend_request": "Petición / identidad",
        "legend_maf": "Flujo multi-agente (MAF)",
        "legend_inference": "Inferencia LLM vía APIM",
        "legend_persistence": "Persistencia (auditoría)",
        "legend_observability": "Observabilidad",
        "legend_governance": "Gobernanza (protege)",
        "legend_steps_title": "PASOS DEL FLUJO",
        "legend_steps_desc": "numerados en orden de ejecución (1→9)",
        "legend_steps_hint": "leer arriba→abajo, izq→der",
        "entra_subtitle": "Proveedor de identidad (OIDC)",
        "fastapi_bullet_1": "▸ /api/claims · WebSocket /ws",
        "fastapi_bullet_2": "▸ Validación JWT (vs Entra)",
        "fastapi_bullet_3": "▸ Protección anti prompt-injection",
        "fastapi_bullet_4": "▸ Managed Identity → Azure",
        "kv_subtitle": "Almacén de secretos · accedido vía MI",
        "kv_desc": "Clave APIM · clave OpenAI · firma JWT",
        "maf_zone_title": "MICROSOFT AGENT FRAMEWORK · GRAFO SECUENCIAL",
        "orch_title": "Orquestador",
        "orch_subtitle": "Plan · Stream · Fallback · Auditoría",
        "agent_intake_title": "Agente Intake",
        "agent_intake_desc_1": "Extrae datos estructurados del siniestro",
        "agent_intake_desc_2": "multilingüe · structured-output (Pydantic)",
        "agent_intake_desc_3": "consulta póliza + cliente",
        "agent_risk_title": "Agente Risk",
        "agent_risk_desc_1": "Puntuación de riesgo 0-100 + detección de fraude",
        "agent_risk_desc_2": "cobertura póliza · historial cliente",
        "agent_risk_desc_3": "señal de fraude · explicabilidad",
        "agent_compliance_title": "Agente Compliance",
        "agent_compliance_desc_1": "Reglas regulatorias + protección anti-injection",
        "agent_compliance_desc_2": "regex determinista · veredicto LLM",
        "agent_compliance_desc_3": "detección de override · modo DAN",
        "apim_subtitle": "Punto único de política y auditoría",
        "apim_bullet_1": "▸ Content Safety · detección jailbreak",
        "apim_bullet_2": "▸ Límite tokens · rate-limit por agente",
        "apim_bullet_3": "▸ Audit logs · cabecera X-Agent-Id",
        "apim_bullet_4": "▸ Managed Identity → AOAI",
        "aoai_desc_1": "endpoint privado · auth MI · streaming",
        "aoai_desc_2": "DefaultAzureCredential / fallback az CLI",
        "cosmos_subtitle": "NoSQL · audit trail",
        "cosmos_desc": "claims · trazas · log de gobernanza",
        "blob_subtitle": "Evidencias (PDFs · fotos)",
        "blob_desc": "partes · daños · documentación",
        "appins_subtitle": "Telemetría de toda la pila",
        "appins_desc": "trazas · latencia · coste tokens · alertas",
        "thub_title": "Hub de telemetría",
        "thub_subtitle": "APIM + agentes emiten trazas",
        "thub_desc": "X-Agent-Id · métricas safety / coste",
        "github_subtitle": "fuente de verdad · auditoría",
        "codeowners_subtitle": "revisión por dominio",
        "codeowners_desc": "agents · backend · evals · dashboard · infra",
        "evalgate_subtitle": "golden dataset en cada PR",
        "evalgate_desc": "bloquea merge si baja el pass-rate",
        "actions_subtitle": "OIDC federado → Azure",
        "actions_desc": "build · evals · azd up · aprovisionado",
        "banco_title": "REGULATORIO NIVEL BANCO",
        "banco_desc_1": "Mismo rigor que el software bancario crítico:",
        "banco_desc_2": "peer review · evals · OIDC · auditoría · PRs firmados",
        "banco_desc_3": "Ningún humano puede hacer merge sin pasar los checks de gobernanza",
        "arr_inference": "inferencia",
        "arr_audit": "auditoría",
        "arr_evidence": "evidencias",
        "arr_telemetry": "telemetría",
        "arr_step_1": "paso 1",
        "arr_step_2": "paso 2",
        "arr_step_3": "paso 3",
    },
    "en": {
        "title_attr": "Insurance AI Agents — Reference Architecture",
        "desc_attr": (
            "Multi-agent claims processing demo: React dashboard, FastAPI backend "
            "on Azure Container Apps, Microsoft Agent Framework orchestrating "
            "Intake / Risk / Compliance agents, Azure OpenAI through APIM AI "
            "Gateway, Cosmos DB and Blob Storage for state, Microsoft Entra ID "
            "for identity, Application Insights for observability, GitHub "
            "Enterprise (CODEOWNERS, Eval Gate, Actions) for governance."
        ),
        "aria_label": "Insurance AI Agents reference architecture",
        "subtitle": (
            "GOVERNED MULTI-AGENT CLAIMS PROCESSING · REFERENCE ARCHITECTURE"
        ),
        "zone_edge": "EDGE · CLIENT TIER",
        "zone_azure": "MICROSOFT AZURE · ENTERPRISE TENANT",
        "zone_governance": (
            "GITHUB ENTERPRISE · GOVERNANCE LANE  "
            "(PROTECTS &amp; AUDITS ALL ABOVE)"
        ),
        "users_header": "END USERS · BROWSER",
        "user_customer": "Customer",
        "user_operator": "Operator",
        "role_customer": "role: Customer.Submit",
        "role_operator": "role: Operator.Review",
        "dashboard_bullet_1": "▸ Per-role views",
        "dashboard_bullet_2": "▸ Customer · Operator · Risk",
        "dashboard_bullet_3": "▸ Compliance · Auto-demo",
        "dashboard_bullet_4": "▸ Live WebSocket streaming",
        "legend_title": "LEGEND",
        "legend_request": "Request / identity",
        "legend_maf": "Multi-agent flow (MAF)",
        "legend_inference": "LLM inference via APIM",
        "legend_persistence": "Persistence (audit)",
        "legend_observability": "Observability",
        "legend_governance": "Governance (protects)",
        "legend_steps_title": "FLOW STEPS",
        "legend_steps_desc": "numbered in execution order (1→9)",
        "legend_steps_hint": "read top→bottom, left→right",
        "entra_subtitle": "Identity provider (OIDC)",
        "fastapi_bullet_1": "▸ /api/claims · WebSocket /ws",
        "fastapi_bullet_2": "▸ JWT validation (vs Entra)",
        "fastapi_bullet_3": "▸ Prompt-injection guard",
        "fastapi_bullet_4": "▸ Managed Identity → Azure",
        "kv_subtitle": "Secret store · accessed via MI",
        "kv_desc": "APIM key · OpenAI key · JWT signing",
        "maf_zone_title": "MICROSOFT AGENT FRAMEWORK · SEQUENTIAL GRAPH",
        "orch_title": "Orchestrator",
        "orch_subtitle": "Plan · Stream · Fallback · Audit",
        "agent_intake_title": "Intake Agent",
        "agent_intake_desc_1": "Extracts structured claim data",
        "agent_intake_desc_2": "multilingual · structured-output (Pydantic)",
        "agent_intake_desc_3": "policy + customer lookup",
        "agent_risk_title": "Risk Agent",
        "agent_risk_desc_1": "Risk score 0-100 + fraud detection",
        "agent_risk_desc_2": "policy coverage · customer history",
        "agent_risk_desc_3": "fraud signal · explainability",
        "agent_compliance_title": "Compliance Agent",
        "agent_compliance_desc_1": "Regulatory rules + injection guard",
        "agent_compliance_desc_2": "deterministic regex · LLM verdict",
        "agent_compliance_desc_3": "supervisor override detection · DAN mode",
        "apim_subtitle": "Single point of policy &amp; audit",
        "apim_bullet_1": "▸ Content Safety · jailbreak detect",
        "apim_bullet_2": "▸ Token-limit · rate-limit per agent",
        "apim_bullet_3": "▸ Audit logs · X-Agent-Id header",
        "apim_bullet_4": "▸ Managed Identity → AOAI",
        "aoai_desc_1": "private endpoint · MI auth · streaming",
        "aoai_desc_2": "DefaultAzureCredential / az CLI fallback",
        "cosmos_subtitle": "NoSQL · audit trail",
        "cosmos_desc": "claims · traces · governance log",
        "blob_subtitle": "Evidence (PDFs · photos)",
        "blob_desc": "reports · damage · documentation",
        "appins_subtitle": "Telemetry across the stack",
        "appins_desc": "trace · latency · token cost · alerts",
        "thub_title": "Telemetry hub",
        "thub_subtitle": "APIM + agents emit traces",
        "thub_desc": "X-Agent-Id · safety / cost metrics",
        "github_subtitle": "source of truth · audit",
        "codeowners_subtitle": "per-domain review",
        "codeowners_desc": "agents · backend · evals · dashboard · infra",
        "evalgate_subtitle": "golden dataset on every PR",
        "evalgate_desc": "blocks merge if eval pass-rate drops",
        "actions_subtitle": "federated OIDC → Azure",
        "actions_desc": "build · evals · azd up · provision",
        "banco_title": "BANCO-GRADE REGULATORY",
        "banco_desc_1": "Same rigor as critical banking software:",
        "banco_desc_2": "peer review · evals · OIDC · audit · signed PRs",
        "banco_desc_3": "No human can merge without governance checks passing",
        "arr_inference": "inference",
        "arr_audit": "audit write",
        "arr_evidence": "evidence",
        "arr_telemetry": "telemetry",
        "arr_step_1": "step 1",
        "arr_step_2": "step 2",
        "arr_step_3": "step 3",
    },
}


def build_svg(s: dict[str, str]) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1720 1180" font-family="'Segoe UI', system-ui, sans-serif" role="img" aria-label="{s['aria_label']}">
  <title>{s['title_attr']}</title>
  <desc>{s['desc_attr']}</desc>

  <defs>
    <linearGradient id="canvas" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/>
      <stop offset="1" stop-color="#F4F6FA"/>
    </linearGradient>
    <linearGradient id="edgeBand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#F8F9FB"/>
      <stop offset="1" stop-color="#EAEDF2"/>
    </linearGradient>
    <linearGradient id="azureBand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#EAF4FB"/>
      <stop offset="1" stop-color="#D2E5F6"/>
    </linearGradient>
    <linearGradient id="mafBand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#F4EEFB"/>
      <stop offset="1" stop-color="#E6D8F4"/>
    </linearGradient>
    <linearGradient id="govBand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#EFF6FF"/>
      <stop offset="1" stop-color="#DBEAFE"/>
    </linearGradient>

    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity="0.10"/>
    </filter>
    <filter id="zoneShadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#000" flood-opacity="0.05"/>
    </filter>

    <marker id="arrBlue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0078D4"/></marker>
    <marker id="arrPurple" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5C2D91"/></marker>
    <marker id="arrGray" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5A5A5A"/></marker>
    <marker id="arrRed" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{BRAND_PRIMARY_DARK}"/></marker>

    <symbol id="logoMS" viewBox="0 0 23 23">
      <rect x="1"  y="1"  width="10" height="10" fill="#F25022"/>
      <rect x="12" y="1"  width="10" height="10" fill="#7FBA00"/>
      <rect x="1"  y="12" width="10" height="10" fill="#00A4EF"/>
      <rect x="12" y="12" width="10" height="10" fill="#FFB900"/>
    </symbol>

    <symbol id="logoBrand" viewBox="0 0 100 100">
      <polygon points="50,6 89,28 89,72 50,94 11,72 11,28" fill="{BRAND_PRIMARY_DARK}"/>
      <polygon points="50,18 78,34 78,66 50,82 22,66 22,34" fill="{BRAND_PRIMARY}"/>
      <text x="50" y="64" text-anchor="middle" font-family="'Segoe UI', system-ui, sans-serif" font-size="38" font-weight="700" fill="#FFFFFF">{BRAND_MARK_LETTER}</text>
    </symbol>

    <symbol id="iconReact" viewBox="0 0 24 24">
      <path fill="#61DAFB" d="M14.23 12.004a2.236 2.236 0 0 1-2.235 2.236 2.236 2.236 0 0 1-2.236-2.236 2.236 2.236 0 0 1 2.235-2.236 2.236 2.236 0 0 1 2.236 2.236zm2.648-10.69c-1.346 0-3.107.96-4.888 2.622-1.78-1.653-3.542-2.602-4.887-2.602-.41 0-.783.093-1.106.278-1.375.793-1.683 3.264-.973 6.365C1.98 8.917 0 10.42 0 12.004c0 1.59 1.99 3.097 5.043 4.03-.704 3.113-.39 5.588.988 6.38.32.187.69.275 1.102.275 1.345 0 3.107-.96 4.888-2.624 1.78 1.654 3.542 2.603 4.887 2.603.41 0 .783-.09 1.106-.275 1.374-.792 1.683-3.263.973-6.365C22.02 15.096 24 13.59 24 12.004c0-1.59-1.99-3.097-5.043-4.032.704-3.11.39-5.587-.988-6.38-.318-.184-.688-.277-1.092-.278zm-.005 1.09v.006c.225 0 .406.044.558.127.666.382.955 1.835.73 3.704-.054.46-.142.945-.25 1.44-.96-.236-2.006-.417-3.107-.534-.66-.905-1.345-1.727-2.035-2.447 1.592-1.48 3.087-2.292 4.105-2.295zm-9.77.02c1.012 0 2.514.808 4.11 2.28-.686.72-1.37 1.537-2.02 2.442-1.107.117-2.154.298-3.113.538-.112-.49-.195-.964-.254-1.42-.23-1.868.054-3.32.714-3.707.19-.09.4-.127.563-.132zm4.882 3.05c.455.468.91.992 1.36 1.564-.44-.02-.89-.034-1.345-.034-.46 0-.915.01-1.36.034.44-.572.895-1.096 1.345-1.565zM12 8.1c.74 0 1.477.034 2.202.093.406.582.802 1.203 1.183 1.86.372.64.71 1.29 1.018 1.946-.308.655-.646 1.31-1.013 1.95-.38.66-.773 1.288-1.18 1.87-.728.063-1.466.098-2.21.098-.74 0-1.477-.035-2.202-.093-.406-.582-.802-1.204-1.183-1.86-.372-.64-.71-1.29-1.018-1.946.303-.657.646-1.313 1.013-1.954.38-.66.773-1.286 1.18-1.868.728-.064 1.466-.098 2.21-.098zm-3.635.254c-.24.377-.48.763-.704 1.16-.225.39-.435.782-.635 1.174-.265-.656-.49-1.31-.676-1.947.64-.15 1.315-.283 2.015-.386zm7.26 0c.695.103 1.365.23 2.006.387-.18.632-.405 1.282-.66 1.933-.2-.39-.41-.783-.64-1.174-.225-.392-.465-.774-.705-1.146zm3.063.675c.484.15.944.317 1.375.498 1.732.74 2.852 1.708 2.852 2.476-.005.768-1.125 1.74-2.857 2.475-.42.18-.88.342-1.355.493-.28-.958-.646-1.956-1.1-2.98.45-1.017.81-2.01 1.085-2.964zm-13.395.004c.278.96.645 1.957 1.1 2.98-.45 1.017-.812 2.01-1.086 2.964-.484-.15-.944-.318-1.37-.5-1.732-.737-2.852-1.706-2.852-2.474 0-.768 1.12-1.742 2.852-2.476.42-.18.88-.342 1.356-.494zm11.678 4.28c.265.657.49 1.312.676 1.948-.64.157-1.316.29-2.016.39.24-.375.48-.762.705-1.158.225-.39.435-.788.636-1.18zm-9.945.02c.2.392.41.783.64 1.175.23.39.465.772.705 1.143-.695-.102-1.365-.23-2.006-.386.18-.63.406-1.282.66-1.933zM17.92 16.32c.112.493.2.968.254 1.423.23 1.868-.054 3.32-.714 3.708-.147.09-.338.128-.563.128-1.012 0-2.514-.807-4.11-2.28.686-.72 1.37-1.536 2.02-2.44 1.107-.118 2.154-.3 3.113-.54zm-11.83.01c.96.234 2.006.415 3.107.532.66.905 1.345 1.727 2.035 2.446-1.595 1.483-3.092 2.295-4.11 2.295-.22-.005-.406-.05-.553-.132-.666-.38-.955-1.834-.73-3.703.054-.46.142-.944.25-1.438zm4.56.64c.44.02.89.034 1.345.034.46 0 .915-.01 1.36-.034-.44.572-.895 1.095-1.345 1.565-.455-.47-.91-.993-1.36-1.565z"/>
    </symbol>

    <symbol id="iconFastAPI" viewBox="0 0 24 24">
      <path fill="#009688" d="M12 .0387C5.3729.0384.0003 5.3931 0 11.9988c-.001 6.6066 5.372 11.9628 12 11.9625 6.628.0003 12.001-5.3559 12-11.9625-.0003-6.6057-5.3729-11.9604-12-11.96m-.829 5.4153h7.55l-7.5805 5.3284h5.1828L5.279 18.5436q2.9466-6.5444 5.892-13.0896"/>
    </symbol>

    <symbol id="iconGitHub" viewBox="0 0 24 24">
      <path fill="#181717" d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
    </symbol>

    <symbol id="iconActions" viewBox="0 0 24 24">
      <path fill="#2088FF" d="M10.984 13.836a.5.5 0 0 1-.353-.146l-.745-.743a.5.5 0 1 1 .706-.708l.392.391 1.181-1.18a.5.5 0 0 1 .708.707l-1.535 1.533a.504.504 0 0 1-.354.146zm9.353-.147l1.534-1.532a.5.5 0 0 0-.707-.707l-1.181 1.18-.392-.391a.5.5 0 1 0-.706.708l.746.743a.497.497 0 0 0 .706-.001zM4.527 7.452l2.557-1.585A1 1 0 0 0 7.09 4.17L4.533 2.56A1 1 0 0 0 3 3.406v3.196a1.001 1.001 0 0 0 1.527.85zm2.03-2.436L4 6.602V3.406l2.557 1.61zM24 12.5c0 1.93-1.57 3.5-3.5 3.5a3.503 3.503 0 0 1-3.46-3h-2.08a3.503 3.503 0 0 1-3.46 3 3.502 3.502 0 0 1-3.46-3h-.558c-.972 0-1.85-.399-2.482-1.042V17c0 1.654 1.346 3 3 3h.04c.244-1.693 1.7-3 3.46-3 1.93 0 3.5 1.57 3.5 3.5S13.43 24 11.5 24a3.502 3.502 0 0 1-3.46-3H8c-2.206 0-4-1.794-4-4V9.899A5.008 5.008 0 0 1 0 5c0-2.757 2.243-5 5-5s5 2.243 5 5a5.005 5.005 0 0 1-4.952 4.998A2.482 2.482 0 0 0 7.482 12h.558c.244-1.693 1.7-3 3.46-3a3.502 3.502 0 0 1 3.46 3h2.08a3.503 3.503 0 0 1 3.46-3c1.93 0 3.5 1.57 3.5 3.5zm-15 8c0 1.378 1.122 2.5 2.5 2.5s2.5-1.122 2.5-2.5-1.122-2.5-2.5-2.5S9 19.122 9 20.5zM5 9c2.206 0 4-1.794 4-4S7.206 1 5 1 1 2.794 1 5s1.794 4 4 4zm9 3.5c0-1.378-1.122-2.5-2.5-2.5S9 11.122 9 12.5s1.122 2.5 2.5 2.5 2.5-1.122 2.5-2.5zm9 0c0-1.378-1.122-2.5-2.5-2.5S18 11.122 18 12.5s1.122 2.5 2.5 2.5 2.5-1.122 2.5-2.5zm-13 8a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0zm2 0a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0zm12 0c0 1.93-1.57 3.5-3.5 3.5a3.503 3.503 0 0 1-3.46-3.002c-.007.001-.013.005-.021.005l-.506.017h-.017a.5.5 0 0 1-.016-.999l.506-.017c.018-.002.035.006.052.007A3.503 3.503 0 0 1 20.5 17c1.93 0 3.5 1.57 3.5 3.5zm-1 0c0-1.378-1.122-2.5-2.5-2.5S18 19.122 18 20.5s1.122 2.5 2.5 2.5 2.5-1.122 2.5-2.5z"/>
    </symbol>

    <symbol id="iconAPIM" viewBox="0 0 18 18">
      <defs>
        <linearGradient id="apimA" x1="9" y1="16.82" x2="9" y2="1.18" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#198ab3"/><stop offset=".09" stop-color="#1f9dc4"/><stop offset=".24" stop-color="#28b5d9"/><stop offset=".4" stop-color="#2dc6e9"/><stop offset=".57" stop-color="#31d1f2"/><stop offset=".78" stop-color="#32d4f5"/></linearGradient>
        <linearGradient id="apimB" x1="8.36" y1="11.35" x2="8.36" y2="14.46" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#c69aeb"/><stop offset="1" stop-color="#6f4bb2"/></linearGradient>
      </defs>
      <path d="M14.18 5.89a4.85 4.85 0 00-4.95-4.71 5 5 0 00-4.75 3.29A4.61 4.61 0 00.5 9a4.67 4.67 0 004.79 4.5 3 3 0 00.42 0h1.2a1.47 1.47 0 01-.11-.56 1.51 1.51 0 01.2-.73H5.29A3.41 3.41 0 011.77 9a3.33 3.33 0 012.91-3.27l.76-.12.25-.73a3.73 3.73 0 013.54-2.43 3.6 3.6 0 013.68 3.45V7l1.09.15a2.59 2.59 0 012.26 2.49 2.63 2.63 0 01-2.62 2.54h-1.23A3.92 3.92 0 008.54 9a.64.64 0 100 1.27 2.65 2.65 0 010 5.29.64.64 0 100 1.27 3.92 3.92 0 003.87-3.34h1.05a.64.64 0 00.2 0 3.91 3.91 0 003.84-3.85 3.86 3.86 0 00-3.32-3.75z" fill="url(#apimA)"/>
      <rect x="6.8" y="11.35" width="3.12" height="3.12" rx="1.54" fill="url(#apimB)"/>
    </symbol>

    <symbol id="iconCosmos" viewBox="0 0 18 18">
      <defs>
        <radialGradient id="cosmoA" cx="-105.006" cy="-10.409" r="5.954" gradientTransform="matrix(1.036 0 0 1.027 117.739 19.644)" gradientUnits="userSpaceOnUse"><stop offset=".183" stop-color="#5ea0ef"/><stop offset="1" stop-color="#0078d4"/></radialGradient>
        <clipPath id="cosmoB"><path d="M14.969 7.53a6.137 6.137 0 11-7.395-4.543 6.137 6.137 0 017.395 4.543z" fill="none"/></clipPath>
      </defs>
      <path d="M2.954 5.266a.175.175 0 01-.176-.176A2.012 2.012 0 00.769 3.081a.176.176 0 01-.176-.175.176.176 0 01.176-.176A2.012 2.012 0 002.778.72a.175.175 0 01.176-.176.175.175 0 01.176.176 2.012 2.012 0 002.009 2.009.175.175 0 01.176.176.175.175 0 01-.176.176A2.011 2.011 0 003.13 5.09a.177.177 0 01-.176.176zM15.611 17.456a.141.141 0 01-.141-.141 1.609 1.609 0 00-1.607-1.607.141.141 0 01-.141-.14.141.141 0 01.141-.141 1.608 1.608 0 001.607-1.607.141.141 0 01.141-.141.141.141 0 01.141.141 1.608 1.608 0 001.607 1.607.141.141 0 110 .282 1.609 1.609 0 00-1.607 1.607.141.141 0 01-.141.14z" fill="#50e6ff"/>
      <path d="M14.969 7.53a6.137 6.137 0 11-7.395-4.543 6.137 6.137 0 017.395 4.543z" fill="url(#cosmoA)"/>
      <g clip-path="url(#cosmoB)" fill="#f2f2f2"><path d="M5.709 13.115a1.638 1.638 0 10.005-3.275 1.307 1.307 0 00.007-.14A1.651 1.651 0 004.06 8.064H2.832a6.251 6.251 0 001.595 5.051zM15.045 7.815c0-.015 0-.03-.007-.044a5.978 5.978 0 00-1.406-2.88 1.825 1.825 0 00-.289-.09 1.806 1.806 0 00-2.3 1.663 2 2 0 00-.2-.013 1.737 1.737 0 00-.581 3.374 1.451 1.451 0 00.541.1h2.03a13.453 13.453 0 002.212-2.11z"/></g>
      <path d="M17.191 3.832c-.629-1.047-2.1-1.455-4.155-1.149a14.606 14.606 0 00-2.082.452 6.456 6.456 0 011.528.767c.241-.053.483-.116.715-.151a7.49 7.49 0 011.103-.089 2.188 2.188 0 011.959.725c.383.638.06 1.729-.886 3a16.723 16.723 0 01-4.749 4.051A16.758 16.758 0 014.8 13.7c-1.564.234-2.682 0-3.065-.636s-.06-1.73.886-2.995c.117-.157.146-.234.279-.392a6.252 6.252 0 01.026-1.63 11.552 11.552 0 00-1.17 1.372C.517 11.076.181 12.566.809 13.613a3.165 3.165 0 002.9 1.249 8.434 8.434 0 001.251-.1 17.855 17.855 0 006.219-2.4A17.808 17.808 0 0016.24 8.03c1.243-1.661 1.579-3.15.951-4.198z" fill="#50e6ff"/>
    </symbol>

    <symbol id="iconStorage" viewBox="0 0 18 18">
      <defs><linearGradient id="storA" x1="9" y1="15.83" x2="9" y2="5.79" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#b3b3b3"/><stop offset=".26" stop-color="#c1c1c1"/><stop offset="1" stop-color="#e6e6e6"/></linearGradient></defs>
      <path d="M.5 5.79h17v9.48a.57.57 0 01-.57.57H1.07a.57.57 0 01-.57-.57V5.79z" fill="url(#storA)"/>
      <path d="M1.07 2.17h15.86a.57.57 0 01.57.57v3.05H.5V2.73a.57.57 0 01.57-.56z" fill="#37c2b1"/>
      <path d="M2.81 6.89h12.37a.27.27 0 01.26.27v1.4a.27.27 0 01-.26.27H2.81a.27.27 0 01-.26-.27v-1.4a.27.27 0 01.26-.27z" fill="#fff"/>
      <path d="M2.82 9.68h12.37a.27.27 0 01.26.27v1.41a.27.27 0 01-.26.27H2.82a.27.27 0 01-.26-.27V10a.27.27 0 01.26-.32z" fill="#37c2b1"/>
      <path d="M2.82 12.5h12.37a.27.27 0 01.26.27v1.41a.27.27 0 01-.26.27H2.82a.27.27 0 01-.26-.27v-1.41a.27.27 0 01.26-.27z" fill="#258277"/>
    </symbol>

    <symbol id="iconKeyVault" viewBox="0 0 18 18">
      <defs>
        <radialGradient id="kvA" cx="9" cy="9" r="8.5" gradientUnits="userSpaceOnUse"><stop offset=".18" stop-color="#5ea0ef"/><stop offset=".56" stop-color="#5c9fee"/><stop offset=".69" stop-color="#559ced"/><stop offset=".78" stop-color="#4a97e9"/><stop offset=".86" stop-color="#3990e4"/><stop offset=".93" stop-color="#2387de"/><stop offset=".99" stop-color="#087bd6"/><stop offset="1" stop-color="#0078d4"/></radialGradient>
        <radialGradient id="kvB" cx="38.95" cy="182.07" r="9.88" gradientTransform="matrix(.94 0 0 .94 -28.71 -163.24)" gradientUnits="userSpaceOnUse"><stop offset=".27" stop-color="#ffd70f"/><stop offset=".49" stop-color="#ffcb12"/><stop offset=".88" stop-color="#feac19"/><stop offset="1" stop-color="#fea11b"/></radialGradient>
      </defs>
      <path d="M9 .5A8.5 8.5 0 1017.5 9 8.51 8.51 0 009 .5zm0 15.84A7.34 7.34 0 1116.34 9 7.34 7.34 0 019 16.34z" fill="url(#kvA)"/>
      <circle cx="9" cy="9" r="7.34" fill="#fff"/>
      <path d="M13.44 7.33a1.84 1.84 0 000-2.59l-3.15-3.16a1.83 1.83 0 00-2.58 0L4.56 4.74a1.84 1.84 0 000 2.59L7.18 10a.51.51 0 01.15.36v4.88a.63.63 0 00.18.44l1.2 1.2a.41.41 0 00.58 0l1.16-1.16.68-.68a.25.25 0 000-.34l-.49-.49a.27.27 0 010-.37l.49-.49a.25.25 0 000-.34l-.49-.49a.27.27 0 010-.37l.49-.49a.25.25 0 000-.34l-.68-.69v-.25zM9 2.35a1 1 0 010 2.07 1 1 0 110-2.07z" fill="url(#kvB)"/>
      <path d="M8.18 15.3a.23.23 0 00.38-.17v-4a.24.24 0 00-.11-.2.22.22 0 00-.34.2v4a.28.28 0 00.07.17z" fill="#ff9300" opacity=".75"/>
      <rect x="6.48" y="5.79" width="5.17" height=".61" rx=".28" fill="#ff9300" opacity=".75"/>
      <rect x="6.48" y="6.78" width="5.17" height=".61" rx=".28" fill="#ff9300" opacity=".75"/>
    </symbol>

    <symbol id="iconAppInsights" viewBox="0 0 18 18">
      <defs>
        <radialGradient id="aiA" cx="9" cy="7.35" r="6.42" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#b77af4"/><stop offset=".21" stop-color="#b378f2"/><stop offset=".43" stop-color="#a672ed"/><stop offset=".65" stop-color="#9267e4"/><stop offset=".88" stop-color="#7559d8"/><stop offset="1" stop-color="#624fd0"/></radialGradient>
        <linearGradient id="aiB" x1="9.02" y1="3.91" x2="9.08" y2="11.49" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#f2f2f2"/><stop offset=".23" stop-color="#f1f1f2" stop-opacity=".99"/><stop offset=".37" stop-color="#ededf1" stop-opacity=".95"/><stop offset=".48" stop-color="#e7e5f0" stop-opacity=".89"/><stop offset=".58" stop-color="#dedbee" stop-opacity=".81"/><stop offset=".67" stop-color="#d3ceeb" stop-opacity=".7"/><stop offset=".76" stop-color="#c4bee8" stop-opacity=".57"/><stop offset=".84" stop-color="#b4abe5" stop-opacity=".41"/><stop offset=".92" stop-color="#a095e1" stop-opacity=".22"/><stop offset=".99" stop-color="#8b7ddc" stop-opacity=".02"/><stop offset="1" stop-color="#897bdc" stop-opacity="0"/></linearGradient>
      </defs>
      <path d="M10.23 17.39l.81-.87V14.2H7v2.32l.81.87a.32.32 0 00.19.11h2a.32.32 0 00.23-.11z" fill="#cecece"/>
      <path d="M9 .5a5.89 5.89 0 00-5.91 6.57c.27 2.47 2.62 3.62 3.29 6.75a.49.49 0 00.47.38h4.3a.49.49 0 00.47-.38c.67-3.13 3-4.28 3.29-6.75A5.89 5.89 0 009 .5zM7 14.2" fill="url(#aiA)"/>
      <path d="M11.46 3.79a1.4 1.4 0 00-1.35 1.44V6H8v-.77a1.41 1.41 0 00-1.41-1.44 1.4 1.4 0 00-1.35 1.44 1.41 1.41 0 001.35 1.45h.64v6a.36.36 0 00.72 0v-6h2.16v6a.36.36 0 10.72 0v-6h.63a1.4 1.4 0 001.35-1.45 1.4 1.4 0 00-1.35-1.44zM7.23 6h-.68a.74.74 0 01-.68-.77.74.74 0 01.68-.77.74.74 0 01.68.77zm4.28 0h-.68v-.81a.68.68 0 111.35 0 .73.73 0 01-.67.81z" fill="url(#aiB)"/>
      <path fill="#999" d="M6.96 15.8l4.08-.79v-.45l-4.08.8v.44zM11.04 16.11v-.44l-4.08.81v.04l.31.34 3.77-.75z"/>
    </symbol>

    <symbol id="iconAOAI" viewBox="0 0 18 18">
      <defs><linearGradient id="aoaiA" x1="9" y1="19.13" x2="9" y2="-.29" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#0078d4"/><stop offset=".16" stop-color="#1380da"/><stop offset=".53" stop-color="#3c91e5"/><stop offset=".82" stop-color="#559cec"/><stop offset="1" stop-color="#5ea0ef"/></linearGradient></defs>
      <path d="M18 11.38a4 4 0 00-3.51-3.88 5.1 5.1 0 00-5.25-4.88A5.25 5.25 0 004.22 6 4.8 4.8 0 000 10.67a4.9 4.9 0 005.07 4.71h8.65a.78.78 0 00.22 0 4.1 4.1 0 004.06-4z" fill="url(#aoaiA)"/>
      <path d="M5.42 10.39h-.88a1.09 1.09 0 100 .49h.88a.2.2 0 01.2.2v4.3h.49v-4.3a.69.69 0 00-.69-.69zm-1.95.88a.64.64 0 11.64-.64.64.64 0 01-.64.64z" fill="#9cebff"/>
      <path d="M8.94 10.61v-1a.7.7 0 00-.7-.7H6.69a.2.2 0 01-.2-.2V3.4l-.23.12-.26.14v5a.69.69 0 00.69.69h1.55a.21.21 0 01.21.21v1a1.08 1.08 0 00-.85 1.06 1.09 1.09 0 101.34-1.06zm-.25 1.7a.64.64 0 11.64-.64.64.64 0 01-.64.64z" fill="#f2f2f2"/>
      <path d="M14.53 8.5a1.09 1.09 0 00-.25 2.15v.2a.21.21 0 01-.21.21h-2V7.54a.69.69 0 00-.69-.69h-1.03A1.08 1.08 0 009.29 6a1.09 1.09 0 101.06 1.34h1.07a.2.2 0 01.2.2v7.84h.49v-3.83h2a.7.7 0 00.7-.7v-.2a1.09 1.09 0 00.85-1.06 1.09 1.09 0 00-1.13-1.09zm-5.24-.77a.64.64 0 11.64-.64.64.64 0 01-.64.64zm5.24 2.5a.64.64 0 11.63-.64.64.64 0 01-.63.64z" fill="#9cebff"/>
    </symbol>

    <symbol id="iconEntra" viewBox="0 0 18 18">
      <defs>
        <linearGradient id="entrA" x1="13.25" y1="13.02" x2="8.62" y2="4.25" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#1988d9"/><stop offset=".9" stop-color="#54aef0"/></linearGradient>
        <linearGradient id="entrB" x1="11.26" y1="10.47" x2="14.46" y2="15.99" gradientUnits="userSpaceOnUse"><stop offset=".1" stop-color="#54aef0"/><stop offset=".29" stop-color="#4fabee"/><stop offset=".51" stop-color="#41a2e9"/><stop offset=".74" stop-color="#2a93e0"/><stop offset=".88" stop-color="#1988d9"/></linearGradient>
      </defs>
      <path fill="#50e6ff" d="M1.01 10.19l7.92 5.14 8.06-5.16L18 11.35l-9.07 5.84L0 11.35l1.01-1.16z"/>
      <path fill="#fff" d="M1.61 9.53L8.93.81l7.47 8.73-7.47 4.72-7.32-4.73z"/>
      <path fill="#50e6ff" d="M8.93.81v13.45L1.61 9.53 8.93.81z"/>
      <path fill="url(#entrA)" d="M8.93.81v13.45l7.47-4.72L8.93.81z"/>
      <path fill="#53b1e0" d="M8.93 7.76l7.47 1.78-7.47 4.72v-6.5z"/>
      <path fill="#9cebff" d="M8.93 14.26L1.61 9.53l7.32-1.77v6.5z"/>
      <path fill="url(#entrB)" d="M8.93 17.19L18 11.35l-1.01-1.18-8.06 5.16v1.86z"/>
    </symbol>

    <symbol id="iconContainer" viewBox="0 0 18 18">
      <defs><linearGradient id="ccA" x1="9" y1="11.95" x2="9" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#0078d4"/><stop offset=".16" stop-color="#1380da"/><stop offset=".53" stop-color="#3c91e5"/><stop offset=".82" stop-color="#559cec"/><stop offset="1" stop-color="#5ea0ef"/></linearGradient></defs>
      <path d="M17.43 8.21a3.78 3.78 0 00-3.29-3.64A4.77 4.77 0 009.22 0a4.91 4.91 0 00-4.68 3.19 4.52 4.52 0 00-4 4.35A4.6 4.6 0 005.32 12h8.31a3.84 3.84 0 003.8-3.79z" fill="url(#ccA)"/>
      <path d="M6.36 6.46L9 3.87a.3.3 0 01.43 0L12 6.46a.13.13 0 01-.1.23h-1.62a.15.15 0 00-.14.14v3.24a.11.11 0 01-.11.11H8.29a.11.11 0 01-.11-.11V6.83a.14.14 0 00-.13-.14h-1.6a.13.13 0 01-.09-.23z" fill="#f2f2f2"/>
      <path d="M14 11.37a.13.13 0 00-.09-.13L9.16 9.65H9V18h.13l4.71-1.88A.13.13 0 0014 16z" fill="#a67af4"/>
      <path d="M9 9.68l-4.51.83a.14.14 0 00-.12.13v6.23a.15.15 0 00.11.14L9 18a.13.13 0 00.16-.13v-8A.14.14 0 009 9.68z" fill="#552f99"/>
      <path fill="#b77af4" opacity=".75" d="M6.92 10.92v5.81l1.57.25v-6.33l-1.57.27zM4.98 11.24v5.08l1.37.28v-5.59l-1.37.23z"/>
    </symbol>

    <symbol id="iconUser" viewBox="0 0 48 48">
      <circle cx="24" cy="16" r="9" fill="#FFFFFF" stroke="#1F1F1F" stroke-width="1.5"/>
      <path d="M6 44 C 8 30, 16 28, 24 28 C 32 28, 40 30, 42 44" fill="#FFFFFF" stroke="#1F1F1F" stroke-width="1.5"/>
    </symbol>
  </defs>

  <rect width="1720" height="1180" fill="url(#canvas)"/>

  <rect x="0" y="0" width="1720" height="104" fill="#FFFFFF"/>
  <rect x="0" y="103" width="1720" height="2" fill="#E1E4E8"/>

  <use href="#logoMS" x="48" y="30" width="44" height="44"/>
  <text x="104" y="60" font-size="22" font-weight="600" fill="#1F1F1F">Microsoft</text>
  <text x="232" y="64" font-size="30" font-weight="200" fill="#9AA0A6">×</text>
  <use href="#logoBrand" x="264" y="24" width="56" height="56"/>
  <text x="332" y="60" font-size="22" font-weight="600" fill="{BRAND_PRIMARY_DARK}">{BRAND_NAME}</text>

  <text x="860" y="48" text-anchor="middle" font-size="24" font-weight="700" fill="#1F1F1F">Insurance AI Agents</text>
  <text x="860" y="76" text-anchor="middle" font-size="12" font-weight="400" letter-spacing="3" fill="#5A5A5A">{s['subtitle']}</text>

  <rect x="1610" y="38" width="68" height="28" rx="14" fill="#F0F2F5" stroke="#D6D9E0" stroke-width="1"/>
  <text x="1644" y="56" text-anchor="middle" font-size="12" font-weight="600" fill="#1F1F1F">v1.0</text>

  <g filter="url(#zoneShadow)"><rect x="40" y="130" width="400" height="830" rx="18" fill="url(#edgeBand)" stroke="#C2C8D4" stroke-width="1.5"/></g>
  <text x="60" y="160" font-size="11" font-weight="700" fill="#5A5A5A" letter-spacing="3">{s['zone_edge']}</text>

  <g filter="url(#zoneShadow)"><rect x="460" y="130" width="1220" height="830" rx="18" fill="url(#azureBand)" stroke="#74B8E8" stroke-width="1.5" stroke-dasharray="7 5"/></g>
  <text x="480" y="160" font-size="11" font-weight="700" fill="#0067B8" letter-spacing="3">{s['zone_azure']}</text>

  <g filter="url(#zoneShadow)"><rect x="40" y="985" width="1640" height="160" rx="18" fill="url(#govBand)" stroke="{BRAND_PRIMARY}" stroke-width="1.5" stroke-dasharray="7 5"/></g>
  <text x="60" y="1015" font-size="11" font-weight="700" fill="{BRAND_PRIMARY_DARK}" letter-spacing="3">{s['zone_governance']}</text>

  <g filter="url(#cardShadow)"><rect x="70" y="180" width="340" height="160" rx="12" fill="#FFFFFF" stroke="#D6D9E0" stroke-width="1.5"/></g>
  <text x="240" y="206" text-anchor="middle" font-size="12" font-weight="700" fill="#5A5A5A" letter-spacing="2">{s['users_header']}</text>
  <use href="#iconUser" x="125" y="222" width="56" height="56"/>
  <text x="153" y="298" text-anchor="middle" font-size="13" font-weight="600" fill="#1F1F1F">{s['user_customer']}</text>
  <text x="153" y="316" text-anchor="middle" font-size="10" fill="#5A5A5A">{s['role_customer']}</text>
  <use href="#iconUser" x="299" y="222" width="56" height="56"/>
  <text x="327" y="298" text-anchor="middle" font-size="13" font-weight="600" fill="#1F1F1F">{s['user_operator']}</text>
  <text x="327" y="316" text-anchor="middle" font-size="10" fill="#5A5A5A">{s['role_operator']}</text>

  <g filter="url(#cardShadow)"><rect x="70" y="390" width="340" height="230" rx="12" fill="#FFFFFF" stroke="#D6D9E0" stroke-width="1.5"/></g>
  <use href="#iconReact" x="96" y="412" width="50" height="50"/>
  <text x="162" y="432" font-size="15" font-weight="700" fill="#1F1F1F">Dashboard</text>
  <text x="162" y="452" font-size="11.5" fill="#5A5A5A">React 18 · TypeScript · Vite</text>
  <line x1="96" y1="482" x2="384" y2="482" stroke="#E1E4E8" stroke-width="1"/>
  <text x="96" y="506" font-size="12" fill="#444">{s['dashboard_bullet_1']}</text>
  <text x="96" y="527" font-size="12" fill="#444">{s['dashboard_bullet_2']}</text>
  <text x="96" y="548" font-size="12" fill="#444">{s['dashboard_bullet_3']}</text>
  <text x="96" y="569" font-size="12" fill="#444">{s['dashboard_bullet_4']}</text>
  <text x="96" y="603" font-size="10" font-style="italic" fill="#888">dashboard/</text>

  <g filter="url(#cardShadow)"><rect x="70" y="655" width="340" height="280" rx="12" fill="#FFFFFF" stroke="#D6D9E0" stroke-width="1"/></g>
  <text x="90" y="683" font-size="12" font-weight="700" fill="#5A5A5A" letter-spacing="2">{s['legend_title']}</text>

  <line x1="90" y1="710" x2="130" y2="710" stroke="#0078D4" stroke-width="2.2" marker-end="url(#arrBlue)"/>
  <text x="140" y="714" font-size="11.5" fill="#1F1F1F">{s['legend_request']}</text>

  <line x1="90" y1="734" x2="130" y2="734" stroke="#5C2D91" stroke-width="2.2" marker-end="url(#arrPurple)"/>
  <text x="140" y="738" font-size="11.5" fill="#1F1F1F">{s['legend_maf']}</text>

  <line x1="90" y1="758" x2="130" y2="758" stroke="{BRAND_PRIMARY_DARK}" stroke-width="2.2" marker-end="url(#arrRed)"/>
  <text x="140" y="762" font-size="11.5" fill="#1F1F1F">{s['legend_inference']}</text>

  <line x1="90" y1="782" x2="130" y2="782" stroke="#5A5A5A" stroke-width="2.2" marker-end="url(#arrGray)"/>
  <text x="140" y="786" font-size="11.5" fill="#1F1F1F">{s['legend_persistence']}</text>

  <line x1="90" y1="806" x2="130" y2="806" stroke="#5C2D91" stroke-width="2" stroke-dasharray="5 3" marker-end="url(#arrPurple)"/>
  <text x="140" y="810" font-size="11.5" fill="#1F1F1F">{s['legend_observability']}</text>

  <line x1="90" y1="830" x2="130" y2="830" stroke="{BRAND_PRIMARY_DARK}" stroke-width="1.5" stroke-dasharray="4 3"/>
  <text x="140" y="834" font-size="11.5" fill="#1F1F1F">{s['legend_governance']}</text>

  <text x="90" y="868" font-size="11" font-weight="700" fill="#5A5A5A" letter-spacing="2">{s['legend_steps_title']}</text>
  <circle cx="100" cy="890" r="10" fill="#0078D4"/><text x="100" y="894" text-anchor="middle" font-size="11" font-weight="700" fill="#FFFFFF">n</text>
  <text x="120" y="894" font-size="11" fill="#444">{s['legend_steps_desc']}</text>
  <text x="90" y="918" font-size="10" font-style="italic" fill="#888">{s['legend_steps_hint']}</text>

  <g filter="url(#cardShadow)"><rect x="485" y="185" width="310" height="120" rx="12" fill="#FFFFFF" stroke="#0078D4" stroke-width="1.5"/></g>
  <use href="#iconEntra" x="505" y="209" width="54" height="54"/>
  <text x="575" y="222" font-size="14" font-weight="700" fill="#1F1F1F">Microsoft Entra ID</text>
  <text x="575" y="242" font-size="11" fill="#5A5A5A">{s['entra_subtitle']}</text>
  <text x="575" y="262" font-size="11" fill="#444">JWT v2.0 · MSAL</text>
  <text x="505" y="288" font-size="10.5" font-style="italic" fill="#888">Customer.Submit · Operator.Review</text>

  <g filter="url(#cardShadow)"><rect x="485" y="345" width="310" height="200" rx="12" fill="#FFFFFF" stroke="#0078D4" stroke-width="2"/></g>
  <use href="#iconContainer" x="505" y="368" width="54" height="54"/>
  <text x="575" y="384" font-size="15" font-weight="700" fill="#1F1F1F">FastAPI Backend</text>
  <text x="575" y="403" font-size="11" font-weight="600" fill="#0078D4">Azure Container Apps</text>
  <use href="#iconFastAPI" x="730" y="340" width="22" height="22"/>
  <line x1="505" y1="435" x2="775" y2="435" stroke="#E1E4E8" stroke-width="1"/>
  <text x="505" y="458" font-size="12" fill="#444">{s['fastapi_bullet_1']}</text>
  <text x="505" y="479" font-size="12" fill="#444">{s['fastapi_bullet_2']}</text>
  <text x="505" y="500" font-size="12" fill="#444">{s['fastapi_bullet_3']}</text>
  <text x="505" y="521" font-size="12" fill="#444">{s['fastapi_bullet_4']}</text>
  <text x="505" y="539" font-size="10" font-style="italic" fill="#888">backend/main.py · auth.py</text>

  <g filter="url(#cardShadow)"><rect x="485" y="585" width="310" height="100" rx="12" fill="#FFFFFF" stroke="#0078D4" stroke-width="1.5"/></g>
  <use href="#iconKeyVault" x="505" y="605" width="50" height="50"/>
  <text x="570" y="618" font-size="14" font-weight="700" fill="#1F1F1F">Azure Key Vault</text>
  <text x="570" y="637" font-size="11" fill="#5A5A5A">{s['kv_subtitle']}</text>
  <text x="505" y="668" font-size="11" fill="#444">{s['kv_desc']}</text>

  <g filter="url(#zoneShadow)"><rect x="820" y="185" width="410" height="640" rx="14" fill="url(#mafBand)" stroke="#7A52C5" stroke-width="1.5"/></g>
  <text x="840" y="212" font-size="11" font-weight="700" fill="#5C2D91" letter-spacing="1.5">{s['maf_zone_title']}</text>

  <g filter="url(#cardShadow)"><rect x="845" y="232" width="360" height="100" rx="12" fill="#FFFFFF" stroke="#5C2D91" stroke-width="2"/></g>
  <g transform="translate(862, 252)"><circle cx="27" cy="27" r="27" fill="#5C2D91"/><text x="27" y="36" text-anchor="middle" font-size="24" font-weight="700" fill="#FFFFFF">◆</text></g>
  <text x="932" y="266" font-size="15" font-weight="700" fill="#1F1F1F">{s['orch_title']}</text>
  <text x="932" y="286" font-size="11.5" fill="#5A5A5A">{s['orch_subtitle']}</text>
  <text x="932" y="307" font-size="10" font-style="italic" fill="#888">agents/orchestrator/agent.py</text>

  <g filter="url(#cardShadow)"><rect x="845" y="365" width="360" height="120" rx="12" fill="#FFFFFF" stroke="#7A52C5" stroke-width="1.5"/></g>
  <g transform="translate(862, 388)"><polygon points="28,4 50,15 50,42 28,53 6,42 6,15" fill="#7A52C5"/><text x="28" y="36" text-anchor="middle" font-size="15" font-weight="800" fill="#FFFFFF">IA</text></g>
  <text x="932" y="398" font-size="15" font-weight="700" fill="#1F1F1F">{s['agent_intake_title']}</text>
  <text x="932" y="419" font-size="11.5" fill="#5A5A5A">{s['agent_intake_desc_1']}</text>
  <text x="932" y="440" font-size="11" fill="#444">{s['agent_intake_desc_2']}</text>
  <text x="932" y="460" font-size="11" fill="#444">{s['agent_intake_desc_3']}</text>
  <text x="932" y="478" font-size="10" font-style="italic" fill="#888">agents/claims-intake/agent.py</text>
  <circle cx="1182" cy="388" r="13" fill="#5C2D91"/>
  <text x="1182" y="393" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">4</text>

  <g filter="url(#cardShadow)"><rect x="845" y="510" width="360" height="120" rx="12" fill="#FFFFFF" stroke="#7A52C5" stroke-width="1.5"/></g>
  <g transform="translate(862, 533)"><polygon points="28,4 50,15 50,42 28,53 6,42 6,15" fill="#7A52C5"/><text x="28" y="36" text-anchor="middle" font-size="15" font-weight="800" fill="#FFFFFF">RA</text></g>
  <text x="932" y="543" font-size="15" font-weight="700" fill="#1F1F1F">{s['agent_risk_title']}</text>
  <text x="932" y="564" font-size="11.5" fill="#5A5A5A">{s['agent_risk_desc_1']}</text>
  <text x="932" y="585" font-size="11" fill="#444">{s['agent_risk_desc_2']}</text>
  <text x="932" y="605" font-size="11" fill="#444">{s['agent_risk_desc_3']}</text>
  <text x="932" y="623" font-size="10" font-style="italic" fill="#888">agents/risk-assessment/agent.py</text>
  <circle cx="1182" cy="533" r="13" fill="#5C2D91"/>
  <text x="1182" y="538" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">5</text>

  <g filter="url(#cardShadow)"><rect x="845" y="655" width="360" height="140" rx="12" fill="#FFFFFF" stroke="{BRAND_PRIMARY_DARK}" stroke-width="2.5"/></g>
  <g transform="translate(862, 678)"><polygon points="28,4 50,15 50,42 28,53 6,42 6,15" fill="#7A52C5"/><text x="28" y="36" text-anchor="middle" font-size="15" font-weight="800" fill="#FFFFFF">CA</text></g>
  <text x="932" y="688" font-size="15" font-weight="700" fill="#1F1F1F">{s['agent_compliance_title']}</text>
  <text x="932" y="709" font-size="11.5" fill="#5A5A5A">{s['agent_compliance_desc_1']}</text>
  <text x="932" y="730" font-size="11" fill="#444">{s['agent_compliance_desc_2']}</text>
  <text x="932" y="750" font-size="11" fill="#444">{s['agent_compliance_desc_3']}</text>
  <text x="932" y="768" font-size="10" font-style="italic" fill="#888">agents/compliance/agent.py · rules.py</text>
  <rect x="1065" y="668" width="64" height="18" rx="3" fill="{BRAND_PRIMARY_DARK}"/>
  <text x="1097" y="681" text-anchor="middle" font-size="10" font-weight="800" fill="#FFFFFF">WOW</text>
  <circle cx="1182" cy="678" r="13" fill="#5C2D91"/>
  <text x="1182" y="683" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">6</text>

  <g filter="url(#cardShadow)"><rect x="1280" y="345" width="320" height="200" rx="12" fill="#FFFFFF" stroke="{BRAND_PRIMARY_DARK}" stroke-width="2.5"/></g>
  <use href="#iconAPIM" x="1300" y="368" width="58" height="58"/>
  <text x="1372" y="384" font-size="15" font-weight="700" fill="#1F1F1F">APIM AI Gateway</text>
  <text x="1372" y="403" font-size="11" font-weight="600" fill="{BRAND_PRIMARY_DARK}">{s['apim_subtitle']}</text>
  <line x1="1300" y1="435" x2="1580" y2="435" stroke="#E1E4E8" stroke-width="1"/>
  <text x="1300" y="458" font-size="12" fill="#444">{s['apim_bullet_1']}</text>
  <text x="1300" y="479" font-size="12" fill="#444">{s['apim_bullet_2']}</text>
  <text x="1300" y="500" font-size="12" fill="#444">{s['apim_bullet_3']}</text>
  <text x="1300" y="521" font-size="12" fill="#444">{s['apim_bullet_4']}</text>
  <text x="1300" y="539" font-size="10" font-style="italic" fill="#888">USE_APIM_GATEWAY=true</text>
  <circle cx="1300" cy="362" r="13" fill="{BRAND_PRIMARY_DARK}"/>
  <text x="1300" y="367" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">7</text>

  <g filter="url(#cardShadow)"><rect x="1280" y="585" width="320" height="120" rx="12" fill="#FFFFFF" stroke="#0078D4" stroke-width="1.5"/></g>
  <use href="#iconAOAI" x="1300" y="605" width="56" height="56"/>
  <text x="1370" y="618" font-size="15" font-weight="700" fill="#1F1F1F">Azure OpenAI</text>
  <text x="1370" y="638" font-size="11" fill="#5A5A5A">gpt-5.4-mini · gpt-realtime-mini</text>
  <text x="1300" y="666" font-size="11" fill="#444">{s['aoai_desc_1']}</text>
  <text x="1300" y="686" font-size="10" font-style="italic" fill="#888">{s['aoai_desc_2']}</text>
  <circle cx="1300" cy="600" r="13" fill="#0078D4"/>
  <text x="1300" y="605" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">8</text>

  <g filter="url(#cardShadow)"><rect x="485" y="855" width="260" height="95" rx="12" fill="#FFFFFF" stroke="#0078D4" stroke-width="1.5"/></g>
  <use href="#iconCosmos" x="500" y="875" width="50" height="50"/>
  <text x="560" y="892" font-size="14" font-weight="700" fill="#1F1F1F">Cosmos DB</text>
  <text x="560" y="910" font-size="11" fill="#5A5A5A">{s['cosmos_subtitle']}</text>
  <text x="500" y="940" font-size="10.5" fill="#444">{s['cosmos_desc']}</text>
  <circle cx="726" cy="872" r="13" fill="#5A5A5A"/>
  <text x="726" y="877" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">9</text>

  <g filter="url(#cardShadow)"><rect x="760" y="855" width="260" height="95" rx="12" fill="#FFFFFF" stroke="#0078D4" stroke-width="1.5"/></g>
  <use href="#iconStorage" x="775" y="875" width="50" height="50"/>
  <text x="836" y="892" font-size="14" font-weight="700" fill="#1F1F1F">Blob Storage</text>
  <text x="836" y="910" font-size="11" fill="#5A5A5A">{s['blob_subtitle']}</text>
  <text x="775" y="940" font-size="10.5" fill="#444">{s['blob_desc']}</text>

  <g filter="url(#cardShadow)"><rect x="1035" y="855" width="290" height="95" rx="12" fill="#FFFFFF" stroke="#7A52C5" stroke-width="1.5"/></g>
  <use href="#iconAppInsights" x="1050" y="872" width="54" height="54"/>
  <text x="1114" y="890" font-size="14" font-weight="700" fill="#1F1F1F">Application Insights</text>
  <text x="1114" y="908" font-size="11" fill="#5A5A5A">{s['appins_subtitle']}</text>
  <text x="1050" y="938" font-size="10.5" fill="#444">{s['appins_desc']}</text>

  <g filter="url(#cardShadow)"><rect x="1340" y="855" width="260" height="95" rx="12" fill="#FFFFFF" stroke="#74B8E8" stroke-width="1.5"/></g>
  <text x="1470" y="884" text-anchor="middle" font-size="14" font-weight="700" fill="#1F1F1F">{s['thub_title']}</text>
  <text x="1470" y="904" text-anchor="middle" font-size="11" fill="#5A5A5A">{s['thub_subtitle']}</text>
  <text x="1355" y="934" font-size="10" fill="#444">{s['thub_desc']}</text>

  <g transform="translate(80, 1052)"><use href="#iconGitHub" width="48" height="48"/></g>
  <text x="144" y="1073" font-size="15" font-weight="700" fill="#181717">GitHub Enterprise</text>
  <text x="144" y="1093" font-size="11" fill="#5A5A5A">{s['github_subtitle']}</text>
  <text x="144" y="1111" font-size="10" font-style="italic" fill="#888">aangell98/insurance-ai-agents</text>

  <g filter="url(#cardShadow)"><rect x="360" y="1040" width="290" height="90" rx="10" fill="#FFFFFF" stroke="{BRAND_PRIMARY_DARK}" stroke-width="1.5"/></g>
  <g transform="translate(380, 1054)">
    <circle cx="14" cy="14" r="9" fill="{BRAND_PRIMARY_DARK}"/>
    <circle cx="30" cy="14" r="9" fill="{BRAND_PRIMARY_DARK}" opacity="0.85"/>
    <circle cx="22" cy="26" r="9" fill="{BRAND_PRIMARY_DARK}" opacity="0.7"/>
  </g>
  <text x="434" y="1065" font-size="13" font-weight="700" fill="#1F1F1F">CODEOWNERS</text>
  <text x="434" y="1083" font-size="11" fill="#5A5A5A">{s['codeowners_subtitle']}</text>
  <text x="380" y="1108" font-size="10.5" fill="#444">{s['codeowners_desc']}</text>
  <text x="380" y="1123" font-size="9.5" font-style="italic" fill="#888">.github/CODEOWNERS</text>

  <g filter="url(#cardShadow)"><rect x="680" y="1040" width="290" height="90" rx="10" fill="#FFFFFF" stroke="{BRAND_PRIMARY_DARK}" stroke-width="1.5"/></g>
  <g transform="translate(700, 1054)">
    <path d="M 18 2 L 34 8 L 34 22 Q 34 32 18 38 Q 2 32 2 22 L 2 8 Z" fill="{BRAND_PRIMARY_DARK}"/>
    <path d="M 11 19 L 16 24 L 25 14" fill="none" stroke="#FFFFFF" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <text x="754" y="1065" font-size="13" font-weight="700" fill="#1F1F1F">Eval Gate</text>
  <text x="754" y="1083" font-size="11" fill="#5A5A5A">{s['evalgate_subtitle']}</text>
  <text x="700" y="1108" font-size="10.5" fill="#444">{s['evalgate_desc']}</text>
  <text x="700" y="1123" font-size="9.5" font-style="italic" fill="#888">evals/ · eval-on-pr.yml</text>

  <g filter="url(#cardShadow)"><rect x="1000" y="1040" width="290" height="90" rx="10" fill="#FFFFFF" stroke="{BRAND_PRIMARY_DARK}" stroke-width="1.5"/></g>
  <use href="#iconActions" x="1020" y="1054" width="40" height="40"/>
  <text x="1074" y="1065" font-size="13" font-weight="700" fill="#1F1F1F">GitHub Actions</text>
  <text x="1074" y="1083" font-size="11" fill="#5A5A5A">{s['actions_subtitle']}</text>
  <text x="1020" y="1108" font-size="10.5" fill="#444">{s['actions_desc']}</text>
  <text x="1020" y="1123" font-size="9.5" font-style="italic" fill="#888">.github/workflows/</text>

  <g filter="url(#cardShadow)"><rect x="1320" y="1040" width="340" height="90" rx="10" fill="{BRAND_PRIMARY}" stroke="{BRAND_PRIMARY_DARK}" stroke-width="1.5"/></g>
  <text x="1340" y="1067" font-size="13" font-weight="800" fill="#FFFFFF" letter-spacing="1">{s['banco_title']}</text>
  <text x="1340" y="1087" font-size="10.5" fill="#FFFFFF">{s['banco_desc_1']}</text>
  <text x="1340" y="1104" font-size="10.5" font-weight="700" fill="#FFFFFF">{s['banco_desc_2']}</text>
  <text x="1340" y="1121" font-size="10" fill="#FFFFFF" opacity="0.85">{s['banco_desc_3']}</text>

  <path d="M 410 445 L 485 445" stroke="#0078D4" stroke-width="2.4" fill="none" marker-end="url(#arrBlue)"/>
  <text x="412" y="435" font-size="10" font-weight="600" fill="#0078D4">HTTPS + JWT</text>
  <circle cx="447" cy="464" r="11" fill="#0078D4"/>
  <text x="447" y="469" text-anchor="middle" font-size="11" font-weight="700" fill="#FFFFFF">1</text>

  <path d="M 640 345 L 640 305" stroke="#0078D4" stroke-width="2" fill="none" stroke-dasharray="5 3" marker-end="url(#arrBlue)"/>
  <text x="648" y="330" font-size="10" font-weight="600" fill="#0078D4">JWKS</text>
  <circle cx="610" cy="322" r="11" fill="#0078D4"/>
  <text x="610" y="327" text-anchor="middle" font-size="11" font-weight="700" fill="#FFFFFF">2</text>

  <path d="M 640 545 L 640 585" stroke="#0078D4" stroke-width="2" fill="none" stroke-dasharray="5 3" marker-end="url(#arrBlue)"/>
  <text x="648" y="572" font-size="10" font-weight="600" fill="#0078D4">MI</text>

  <path d="M 795 445 L 808 445 L 808 282 L 845 282" stroke="#5C2D91" stroke-width="2.4" fill="none" marker-end="url(#arrPurple)"/>
  <circle cx="808" cy="333" r="13" fill="#5C2D91"/>
  <text x="808" y="338" text-anchor="middle" font-size="12" font-weight="700" fill="#FFFFFF">3</text>

  <path d="M 1025 332 L 1025 365" stroke="#5C2D91" stroke-width="2.4" fill="none" marker-end="url(#arrPurple)"/>
  <text x="1035" y="352" font-size="9.5" fill="#5C2D91">{s['arr_step_1']}</text>

  <path d="M 1025 485 L 1025 510" stroke="#5C2D91" stroke-width="2.4" fill="none" marker-end="url(#arrPurple)"/>
  <text x="1035" y="500" font-size="9.5" fill="#5C2D91">{s['arr_step_2']}</text>

  <path d="M 1025 630 L 1025 655" stroke="#5C2D91" stroke-width="2.4" fill="none" marker-end="url(#arrPurple)"/>
  <text x="1035" y="645" font-size="9.5" fill="#5C2D91">{s['arr_step_3']}</text>

  <path d="M 1205 425 L 1248 425 L 1248 445 L 1280 445" stroke="{BRAND_PRIMARY_DARK}" stroke-width="2.4" fill="none" marker-end="url(#arrRed)"/>
  <text x="1212" y="418" font-size="10" font-weight="600" fill="{BRAND_PRIMARY_DARK}">{s['arr_inference']}</text>
  <path d="M 1205 570 L 1248 570 L 1248 445" stroke="{BRAND_PRIMARY_DARK}" stroke-width="2" fill="none" opacity="0.75"/>
  <path d="M 1205 725 L 1248 725 L 1248 445" stroke="{BRAND_PRIMARY_DARK}" stroke-width="2" fill="none" opacity="0.75"/>

  <path d="M 1440 545 L 1440 585" stroke="#0078D4" stroke-width="2.4" fill="none" marker-end="url(#arrBlue)"/>
  <text x="1450" y="570" font-size="10" font-weight="600" fill="#0078D4">MI token</text>

  <path d="M 795 510 L 810 510 L 810 838 L 615 838 L 615 855" stroke="#5A5A5A" stroke-width="2.2" fill="none" marker-end="url(#arrGray)"/>
  <text x="700" y="830" font-size="10" font-weight="600" fill="#5A5A5A">{s['arr_audit']}</text>

  <path d="M 795 480 L 802 480 L 802 845 L 890 845 L 890 855" stroke="#5A5A5A" stroke-width="2.2" fill="none" marker-end="url(#arrGray)"/>
  <text x="815" y="832" font-size="10" font-weight="600" fill="#5A5A5A">{s['arr_evidence']}</text>

  <path d="M 1440 705 L 1440 838 L 1180 838 L 1180 855" stroke="#5C2D91" stroke-width="1.8" fill="none" stroke-dasharray="5 3" marker-end="url(#arrPurple)"/>
  <text x="1290" y="832" font-size="10" font-weight="600" fill="#5C2D91">{s['arr_telemetry']}</text>
</svg>
"""


OUTPUTS = {
    "es": ROOT / "images" / "architecture.svg",
    "en": ROOT / "images" / "architecture-en.svg",
}

if __name__ == "__main__":
    for lang, out_path in OUTPUTS.items():
        svg = build_svg(STRINGS[lang])
        out_path.write_text(svg, encoding="utf-8")
        print(f"Wrote {out_path.relative_to(ROOT)} ({lang}) - {len(svg):,} chars")
