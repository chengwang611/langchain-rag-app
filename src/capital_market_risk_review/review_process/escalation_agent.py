"""Risk Escalation Agent for review workflow."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from .models import ReviewState


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

XXX_ESCALATION_DIRECTORY: dict[str, dict[str, str]] = {
    "critical": {
        "Market": "Chief Market Risk Officer, XXX Capital Markets",
        "Liquidity": "Chief Liquidity Officer, XXX Capital Markets",
        "Counterparty": "Head of Counterparty Credit Risk, XXX Capital Markets",
        "Model": "Chair, Model Risk Committee, XXX Capital Markets",
        "Regulatory": "Chief Compliance Officer, XXX Capital Markets",
        "Operational": "Chief Operating Risk Officer, XXX Capital Markets",
    },
    "high": {
        "Market": "Head of Market Risk, XXX Capital Markets",
        "Liquidity": "Treasury Risk Manager, XXX Capital Markets",
        "Counterparty": "Senior Counterparty Risk Manager, XXX Capital Markets",
        "Model": "Head of Model Risk Management, XXX Capital Markets",
        "Regulatory": "Head of Regulatory Affairs, XXX Capital Markets",
        "Operational": "Head of Operational Risk, XXX Capital Markets",
    },
}

SLACK_CHANNELS: dict[str, str] = {
    "critical": "#xxx-cm-critical-risk-alerts",
    "high": "#xxx-cm-risk-alerts",
    "medium": "#xxx-cm-risk-monitoring",
    "low": "#xxx-cm-risk-log",
}

SERVICENOW_PRIORITY_MAP: dict[str, str] = {
    "critical": "1 - Critical",
    "high": "2 - High",
    "medium": "3 - Moderate",
    "low": "4 - Low",
}


@tool
def classify_findings_by_severity(findings_json: str) -> str:
    """Parse findings and classify by severity tiers."""
    try:
        findings = json.loads(findings_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON", "escalation_required": False})

    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    critical_findings: list = []
    high_findings: list = []

    for finding in findings:
        sev = str(finding.get("severity", "low")).lower()
        counts[sev] = counts.get(sev, 0) + 1
        if sev == "critical":
            critical_findings.append(finding)
        elif sev == "high":
            high_findings.append(finding)

    escalation_required = counts["critical"] > 0 or counts["high"] > 0

    return json.dumps(
        {
            "total_findings": len(findings),
            "severity_counts": counts,
            "escalation_required": escalation_required,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "summary": (
                f"{counts['critical']} critical, {counts['high']} high, "
                f"{counts['medium']} medium, {counts['low']} low findings detected."
            ),
        }
    )


@tool
def send_slack_notification(severity: str, category: str, message: str) -> str:
    """Send risk alert to severity-specific Slack channel (simulated)."""
    channel = SLACK_CHANNELS.get(severity.lower(), "#xxx-cm-risk-log")
    recipient = (
        XXX_ESCALATION_DIRECTORY.get(severity.lower(), {}).get(category, "Risk Management Team, XXX CM")
    )

    record = {
        "channel": channel,
        "recipient_role": recipient,
        "severity": severity,
        "category": category,
        "message_preview": message[:200],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SENT (simulated — wire Slack SDK for production)",
        "delivery_method": "Slack",
    }
    print(f"[SLACK] -> {channel} | {severity.upper()} | {message[:80]}...")
    return json.dumps(record)


@tool
def send_email_notification(severity: str, category: str, subject: str, body: str) -> str:
    """Send risk escalation email (simulated)."""
    recipient = (
        XXX_ESCALATION_DIRECTORY.get(severity.lower(), {}).get(category, "risk.management@xxx.com")
    )

    record = {
        "to": recipient,
        "subject": subject,
        "body_preview": body[:300],
        "severity": severity,
        "category": category,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SENT (simulated — wire SMTP/SendGrid for production)",
        "delivery_method": "Email",
    }
    print(f"[EMAIL] -> {recipient} | Subject: {subject}")
    return json.dumps(record)


@tool
def create_servicenow_ticket(
    category: str,
    severity: str,
    short_description: str,
    detailed_description: str,
) -> str:
    """Create ServiceNow incident ticket (simulated)."""
    priority = SERVICENOW_PRIORITY_MAP.get(severity.lower(), "3 - Moderate")
    assignment_group = f"XXX CM {category} Risk Management"
    ticket_id = f"INC{abs(hash(short_description)) % 10_000_000:07d}"

    record = {
        "ticket_id": ticket_id,
        "priority": priority,
        "assignment_group": assignment_group,
        "short_description": short_description,
        "detailed_description_preview": detailed_description[:300],
        "state": "New",
        "category": category,
        "severity": severity,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CREATED (simulated — wire ServiceNow REST API for production)",
        "servicenow_url": f"https://xxx.service-now.com/incident.do?sys_id={ticket_id}",
    }
    print(f"[SERVICENOW] Ticket {ticket_id} created: {short_description[:60]}")
    return json.dumps(record)


_ESCALATION_TOOLS = [
    classify_findings_by_severity,
    send_slack_notification,
    send_email_notification,
    create_servicenow_ticket,
]
_escalation_llm = llm.bind_tools(_ESCALATION_TOOLS)
_tool_executor = {t.name: t for t in _ESCALATION_TOOLS}

ESCALATION_SYSTEM_PROMPT = """
You are the Risk Escalation Agent for XXX Capital Markets.

Your escalation protocol:
1. ALWAYS start by calling classify_findings_by_severity to understand the severity breakdown.
2. For each CRITICAL finding:
   - send_slack_notification (channel auto-selected by severity)
   - send_email_notification to the designated senior risk officer
   - create_servicenow_ticket with full details and remediation context
3. For each HIGH finding:
   - send_slack_notification
   - create_servicenow_ticket
4. For MEDIUM findings:
   - send_slack_notification only
5. LOW findings:
   - Log only, no notification action required.

After completing all notifications, produce a concise ESCALATION LOG summarising:
  - Total findings processed and severity breakdown
  - All notifications sent (channel, recipient, method)
  - All ServiceNow tickets created (ticket IDs)
  - Overall escalation status (ESCALATED / MONITORED / NO ACTION REQUIRED)
""".strip()


def escalation_agent_node(state: ReviewState) -> dict:
    """Classify findings and route escalations through simulated channels."""
    findings_json = state.get("findings_json", "[]")
    compliance_report = state.get("compliance_report", "")
    market_report = state.get("market_sensitivity_report", "")

    messages: list = [
        HumanMessage(content=ESCALATION_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Risk findings to escalate:\n{findings_json}\n\n"
                f"Compliance assessment:\n{compliance_report}\n\n"
                f"Market sensitivity metrics:\n{market_report}"
            )
        ),
    ]

    response = _escalation_llm.invoke(messages)
    for _ in range(20):
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            tool_fn = _tool_executor.get(tc["name"])
            result = tool_fn.invoke(tc["args"]) if tool_fn else "Tool not found."
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        response = _escalation_llm.invoke(messages)

    escalation_log_text = response.content if hasattr(response, "content") else str(response)

    escalation_required = any(
        '"escalation_required": true' in str(msg.content)
        for msg in messages
        if isinstance(msg, ToolMessage)
    )

    return {
        "escalation_log": [escalation_log_text],
        "escalation_required": escalation_required,
        "messages": [AIMessage(content=f"[Escalation Agent]\n{escalation_log_text}")],
    }
