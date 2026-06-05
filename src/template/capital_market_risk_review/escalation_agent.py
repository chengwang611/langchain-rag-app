"""
escalation_agent.py — Risk Escalation Agent.

Classifies risk findings by severity, autonomously routes critical and high findings
to designated RBC Capital Markets senior risk officers, and dispatches notifications
via Slack, email, and ServiceNow incident tickets.

EXTEND:
- Integrate with real Slack API (slack_sdk) for live channel delivery
- Integrate with SMTP / SendGrid for actual email delivery
- Integrate with ServiceNow REST API for real incident creation
- Add PagerDuty for on-call engineer alerts on critical out-of-hours findings
- Add multi-tier approval chain: L1 analyst → L2 manager → L3 CRO
- Add SLA timer: auto-escalate if no acknowledgment within N hours
- Write full escalation audit log to PostgreSQL for regulatory record-keeping
- Add JIRA integration for engineering-team remediation task tracking
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from src.template.capital_market_risk_review.models import ReviewState


# ── LLM config ────────────────────────────────────────────────────────────────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ── RBC Escalation Directory ──────────────────────────────────────────────────
# EXTEND: load from RBC Active Directory / HR system via Microsoft Graph API
RBC_ESCALATION_DIRECTORY: dict[str, dict[str, str]] = {
    "critical": {
        "Market":      "Chief Market Risk Officer, RBC Capital Markets",
        "Liquidity":   "Chief Liquidity Officer, RBC Capital Markets",
        "Counterparty":"Head of Counterparty Credit Risk, RBC Capital Markets",
        "Model":       "Chair, Model Risk Committee, RBC Capital Markets",
        "Regulatory":  "Chief Compliance Officer, RBC Capital Markets",
        "Operational": "Chief Operating Risk Officer, RBC Capital Markets",
    },
    "high": {
        "Market":      "Head of Market Risk, RBC Capital Markets",
        "Liquidity":   "Treasury Risk Manager, RBC Capital Markets",
        "Counterparty":"Senior Counterparty Risk Manager, RBC Capital Markets",
        "Model":       "Head of Model Risk Management, RBC Capital Markets",
        "Regulatory":  "Head of Regulatory Affairs, RBC Capital Markets",
        "Operational": "Head of Operational Risk, RBC Capital Markets",
    },
}

SLACK_CHANNELS: dict[str, str] = {
    "critical": "#rbc-cm-critical-risk-alerts",
    "high":     "#rbc-cm-risk-alerts",
    "medium":   "#rbc-cm-risk-monitoring",
    "low":      "#rbc-cm-risk-log",
}

SERVICENOW_PRIORITY_MAP: dict[str, str] = {
    "critical": "1 - Critical",
    "high":     "2 - High",
    "medium":   "3 - Moderate",
    "low":      "4 - Low",
}


# ── Tools ──────────────────────────────────────────────────────────────────────

@tool
def classify_findings_by_severity(findings_json: str) -> str:
    """
    Parse and classify risk findings by severity level.
    Returns counts per severity tier and flags whether escalation is required.

    Args:
        findings_json: JSON array string of risk findings (from analyze_node output)
    """
    try:
        findings = json.loads(findings_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON", "escalation_required": False})

    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    critical_findings: list = []
    high_findings: list = []

    for f in findings:
        sev = str(f.get("severity", "low")).lower()
        counts[sev] = counts.get(sev, 0) + 1
        if sev == "critical":
            critical_findings.append(f)
        elif sev == "high":
            high_findings.append(f)

    escalation_required = counts["critical"] > 0 or counts["high"] > 0

    return json.dumps({
        "total_findings": len(findings),
        "severity_counts": counts,
        "escalation_required": escalation_required,
        "critical_findings": critical_findings,
        "high_findings": high_findings,
        "summary": (
            f"{counts['critical']} critical, {counts['high']} high, "
            f"{counts['medium']} medium, {counts['low']} low findings detected."
        ),
    })


@tool
def send_slack_notification(severity: str, category: str, message: str) -> str:
    """
    Send a risk alert to the appropriate RBC Capital Markets Slack channel.
    Channel and recipient role are determined automatically by severity and category.

    Args:
        severity: Severity level (critical, high, medium, low)
        category: Risk category (Market, Liquidity, Counterparty, Model, etc.)
        message: Alert message body (keep under 500 characters for Slack readability)
    """
    channel = SLACK_CHANNELS.get(severity.lower(), "#rbc-cm-risk-log")
    recipient = (
        RBC_ESCALATION_DIRECTORY
        .get(severity.lower(), {})
        .get(category, "Risk Management Team, RBC CM")
    )

    # EXTEND: replace with real Slack API call
    # from slack_sdk import WebClient
    # client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    # client.chat_postMessage(channel=channel, text=message)

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
    print(f"[SLACK] → {channel} | {severity.upper()} | {message[:80]}...")
    return json.dumps(record)


@tool
def send_email_notification(
    severity: str,
    category: str,
    subject: str,
    body: str,
) -> str:
    """
    Send a risk escalation email to the designated RBC Capital Markets risk officer.
    Recipient is resolved from the RBC escalation directory by severity and category.

    Args:
        severity: Severity level (critical, high, medium, low)
        category: Risk category
        subject: Email subject line
        body: Email body (full finding details)
    """
    recipient = (
        RBC_ESCALATION_DIRECTORY
        .get(severity.lower(), {})
        .get(category, "risk.management@rbc.com")
    )

    # EXTEND: replace with real SMTP / SendGrid call
    # import smtplib, ssl
    # with smtplib.SMTP_SSL("smtp.rbc.com", 465, ...) as server:
    #     server.sendmail("risk-pipeline@rbc.com", recipient, msg.as_string())

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
    print(f"[EMAIL] → {recipient} | Subject: {subject}")
    return json.dumps(record)


@tool
def create_servicenow_ticket(
    category: str,
    severity: str,
    short_description: str,
    detailed_description: str,
) -> str:
    """
    Create a ServiceNow incident ticket for a risk finding requiring formal
    remediation tracking. Priority and assignment group are set automatically.

    Args:
        category: Risk category (Market, Liquidity, Counterparty, Model, etc.)
        severity: Severity level (critical, high, medium, low)
        short_description: One-line summary (used as ticket title)
        detailed_description: Full incident description with finding details,
                              regulatory references, and recommended actions
    """
    priority = SERVICENOW_PRIORITY_MAP.get(severity.lower(), "3 - Moderate")
    assignment_group = f"RBC CM {category} Risk Management"

    # Deterministic-looking ticket ID based on description hash
    ticket_id = f"INC{abs(hash(short_description)) % 10_000_000:07d}"

    # EXTEND: replace with real ServiceNow REST API call
    # import requests
    # resp = requests.post(
    #     f"{os.environ['SNOW_INSTANCE']}/api/now/table/incident",
    #     json={"short_description": short_description, "priority": priority, ...},
    #     auth=(os.environ["SNOW_USER"], os.environ["SNOW_PASSWORD"]),
    # )
    # ticket_id = resp.json()["result"]["number"]

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
        "servicenow_url": f"https://rbc.service-now.com/incident.do?sys_id={ticket_id}",
    }
    print(f"[SERVICENOW] Ticket {ticket_id} created: {short_description[:60]}")
    return json.dumps(record)


# ── Agent setup ────────────────────────────────────────────────────────────────
_ESCALATION_TOOLS = [
    classify_findings_by_severity,
    send_slack_notification,
    send_email_notification,
    create_servicenow_ticket,
]
_escalation_llm = llm.bind_tools(_ESCALATION_TOOLS)
_tool_executor = {t.name: t for t in _ESCALATION_TOOLS}

ESCALATION_SYSTEM_PROMPT = """
You are the Risk Escalation Agent for RBC Capital Markets.

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


def escalation_agent_node(state: ReviewState) -> ReviewState:
    """
    Risk Escalation Agent: classifies findings by severity and autonomously routes
    critical/high findings to senior RBC Capital Markets risk officers via Slack,
    email, and ServiceNow using tool-augmented LLM.

    EXTEND:
    - Add PagerDuty for critical after-hours on-call alerts
    - Add JIRA integration for engineering-team remediation tasks
    - Add Twilio SMS for critical findings requiring immediate senior attention
    - Implement acknowledgment tracking: re-alert if no ack within SLA window
    - Write escalation log to PostgreSQL for regulatory audit trail
    - Add multi-tier routing: L1 (analyst) → L2 (manager) → L3 (CRO / Board)
    """
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

    # Agentic loop — higher limit: escalation may fire multiple notifications
    response = _escalation_llm.invoke(messages)  # initialise with first call
    for _ in range(20):
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            tool_fn = _tool_executor.get(tc["name"])
            result = tool_fn.invoke(tc["args"]) if tool_fn else "Tool not found."
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        response = _escalation_llm.invoke(messages)

    escalation_log_text = (
        response.content if hasattr(response, "content") else str(response)
    )

    # Check if escalation was triggered (critical or high findings present)
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

