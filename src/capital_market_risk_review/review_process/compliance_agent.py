"""Regulatory Compliance Agent for review workflow."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from .models import ReviewState


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

BASEL_THRESHOLDS: dict[str, dict] = {
    "Market": {
        "var_limit_utilization_pct": 85.0,
        "stressed_var_multiplier": 3.0,
        "backtesting_breach_limit": 4,
        "description": "Basel III Market Risk — Internal Models Approach (IMA)",
        "regulation_ref": "BCBS 352 / CRR2 Art.325",
    },
    "Liquidity": {
        "lcr_minimum_pct": 100.0,
        "nsfr_minimum_pct": 100.0,
        "model_staleness_months": 6,
        "description": "Basel III LCR / NSFR Liquidity Requirements",
        "regulation_ref": "BCBS 238 / BCBS 295",
    },
    "Counterparty": {
        "cva_capital_charge_threshold_usd": 1_000_000,
        "margin_call_sla_days": 1,
        "description": "Basel III CVA Risk Framework / EMIR Margin Requirements",
        "regulation_ref": "BCBS 325 / EMIR Art.11",
    },
    "Model": {
        "revalidation_period_months": 12,
        "backtesting_breach_limit": 4,
        "description": "SR 11-7 / Basel III Model Risk Management",
        "regulation_ref": "SR 11-7 / OSFI E-23",
    },
    "Regulatory": {
        "reporting_lag_days": 5,
        "description": "Regulatory Reporting SLA — OSFI / SEC / CFTC",
        "regulation_ref": "OSFI Guideline B-2 / Dodd-Frank §4s",
    },
}

XXX_RISK_APPETITE: dict[str, dict] = {
    "Market": {
        "var_limit_utilization_warning_pct": 80.0,
        "var_limit_utilization_breach_pct": 95.0,
        "escalation_owner": "Head of Market Risk, XXX Capital Markets",
        "policy_ref": "XXX CM Market Risk Policy v4.2",
    },
    "Liquidity": {
        "liquidity_buffer_warning_days": 30,
        "liquidity_buffer_breach_days": 10,
        "model_refresh_sla_months": 6,
        "escalation_owner": "Chief Liquidity Officer, XXX Capital Markets",
        "policy_ref": "XXX CM Liquidity Risk Policy v3.1",
    },
    "Counterparty": {
        "margin_call_latency_warning_days": 2,
        "margin_call_latency_breach_days": 3,
        "escalation_owner": "Head of Counterparty Credit Risk, XXX Capital Markets",
        "policy_ref": "XXX CM Counterparty Risk Policy v5.0",
    },
    "Model": {
        "max_model_age_months": 12,
        "regime_change_revalidation_trigger": True,
        "escalation_owner": "Model Risk Committee, XXX Capital Markets",
        "policy_ref": "XXX CM Model Risk Management Framework v2.3",
    },
}


@tool
def check_basel_threshold(category: str, metric: str, observed_value: float) -> str:
    """Check an observed metric against Basel III/IV thresholds."""
    thresholds = BASEL_THRESHOLDS.get(category, {})
    threshold = thresholds.get(metric)

    if threshold is None:
        return json.dumps(
            {
                "status": "unknown",
                "message": f"No Basel threshold defined for {category}.{metric}",
                "available_metrics": [
                    k for k in thresholds if k not in ("description", "regulation_ref")
                ],
            }
        )

    breach = float(observed_value) > float(threshold)
    return json.dumps(
        {
            "category": category,
            "metric": metric,
            "observed_value": observed_value,
            "threshold": threshold,
            "breach": breach,
            "status": "BREACH" if breach else "COMPLIANT",
            "regulatory_rule": thresholds.get("description", ""),
            "regulation_ref": thresholds.get("regulation_ref", ""),
            "remediation_urgency": "immediate" if breach else "monitor",
        }
    )


@tool
def get_xxx_risk_appetite(category: str) -> str:
    """Retrieve XXX internal risk appetite limits and escalation ownership."""
    appetite = XXX_RISK_APPETITE.get(category)
    if appetite is None:
        return json.dumps(
            {
                "status": "not_configured",
                "message": f"No XXX risk appetite configured for category: {category}",
                "available_categories": list(XXX_RISK_APPETITE.keys()),
            }
        )
    return json.dumps({"category": category, "limits": appetite, "status": "retrieved"})


@tool
def generate_remediation_recommendation(category: str, severity: str, breach_description: str) -> str:
    """Generate structured remediation recommendation for a risk breach."""
    sla_map = {
        "critical": "24 hours",
        "high": "3 business days",
        "medium": "5 business days",
        "low": "10 business days",
    }
    owner_map = {
        "Market": "Market Risk Manager, XXX Capital Markets",
        "Liquidity": "Treasury / Asset-Liability Management, XXX CM",
        "Counterparty": "Counterparty Credit Risk team, XXX CM",
        "Model": "Model Risk Management (MRM) team, XXX CM",
        "Regulatory": "Regulatory Reporting team, XXX CM",
        "Operational": "Operational Risk team, XXX CM",
    }
    reg_ref = BASEL_THRESHOLDS.get(category, {}).get("regulation_ref", "XXX CM Internal Policy")
    xxx_policy = XXX_RISK_APPETITE.get(category, {}).get("policy_ref", "XXX CM Risk Policy")

    return json.dumps(
        {
            "category": category,
            "severity": severity,
            "breach_description": breach_description,
            "recommended_action": (
                f"Immediately notify {owner_map.get(category, 'Risk Management')} "
                f"and initiate remediation for: {breach_description}"
            ),
            "responsible_owner": owner_map.get(category, "Risk Management"),
            "due_date_sla": sla_map.get(severity.lower(), "10 business days"),
            "regulatory_reference": reg_ref,
            "xxx_policy_reference": xxx_policy,
            "escalation_required": severity.lower() in ("high", "critical"),
        }
    )


_COMPLIANCE_TOOLS = [
    check_basel_threshold,
    get_xxx_risk_appetite,
    generate_remediation_recommendation,
]
_compliance_llm = llm.bind_tools(_COMPLIANCE_TOOLS)
_tool_executor = {t.name: t for t in _COMPLIANCE_TOOLS}

COMPLIANCE_SYSTEM_PROMPT = """
You are the Regulatory Compliance Agent for XXX Capital Markets.

Your role is to cross-reference the provided risk findings against:
1. Basel III/IV regulatory thresholds — use check_basel_threshold for each applicable metric
2. XXX internal risk appetite limits — use get_xxx_risk_appetite per category
3. Remediation recommendations — use generate_remediation_recommendation for each high/critical breach

Process ALL findings systematically. For each finding:
  - Call check_basel_threshold with the relevant metric
  - Call get_xxx_risk_appetite for the category
  - Call generate_remediation_recommendation if severity is high or critical

Produce a structured compliance report with:
  COMPLIANCE STATUS: (BREACH / COMPLIANT / PARTIAL)
  - Per-finding breach flags with applicable Basel/OSFI regulation refs
  - XXX internal limit comparison
  - Prioritised remediation actions with owners, SLAs, and policy references
""".strip()


def compliance_agent_node(state: ReviewState) -> dict:
    """Cross-reference findings against Basel and internal risk appetite limits."""
    findings_json = state.get("findings_json", "[]")

    messages: list = [
        HumanMessage(content=COMPLIANCE_SYSTEM_PROMPT),
        HumanMessage(content=f"Risk findings to assess:\n{findings_json}"),
    ]

    response = _compliance_llm.invoke(messages)
    for _ in range(12):
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            tool_fn = _tool_executor.get(tc["name"])
            result = tool_fn.invoke(tc["args"]) if tool_fn else "Tool not found."
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        response = _compliance_llm.invoke(messages)

    compliance_report = response.content if hasattr(response, "content") else str(response)

    return {
        "compliance_report": compliance_report,
        "messages": [AIMessage(content=f"[Compliance Agent]\n{compliance_report}")],
    }
