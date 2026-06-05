"""
analyze.py — LLM-powered risk analysis and findings extraction.

EXTEND:
- Swap to a larger model (gpt-4o) for higher-stakes documents
- Add chain-of-thought prompting for better reasoning transparency
- Add self-consistency: run N times and vote on findings
- Add confidence scoring per finding
- Add citation extraction: map each finding back to exact chunk
- Add regulatory mapping: FRTB, Basel III, CCAR, DFAST references
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.template.capital_market_risk_review.models import ReviewState


# ── LLM config ───────────────────────────────────────────────────────────────
# EXTEND: use AzureChatOpenAI for enterprise Azure OpenAI deployments
# EXTEND: set max_tokens to control cost on large documents
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ── System prompt ─────────────────────────────────────────────────────────────
# EXTEND: add firm-specific risk taxonomy, regulatory context,
#         or few-shot examples of good findings
SYSTEM_PROMPT = """
You are a senior capital-markets risk reviewer at a tier-1 bank.
Your role is to:
1. Write a concise executive summary (3-5 sentences) of material risk issues.
2. Extract a JSON array of structured findings.

Each finding must have these fields:
  - category: one of Market, Liquidity, Counterparty, Model, Operational, Regulatory, Other
  - severity: one of low, medium, high, critical
  - snippet: exact quoted text from the provided context (evidence)
  - rationale: your reasoning for the severity assessment
  - source_id: the [source_id] label from the context

Rules:
- Base all statements strictly on provided context. Do not hallucinate.
- If evidence is insufficient, state that explicitly in the summary.
- Format output as:
  SUMMARY:
  <executive summary text>

  JSON:
  <json array of findings>
""".strip()


def analyze_node(state: ReviewState) -> ReviewState:
    """
    Run LLM over retrieved chunks to produce draft summary + findings.

    EXTEND:
    - Add a critique/reflection step: ask LLM to challenge its own findings
    - Split into two nodes: one for summary, one for structured extraction
    - Add output validation: parse JSON and retry on schema errors
    - Log token usage for cost tracking
    """
    # Build context from retrieved chunks
    context = "\n\n---\n\n".join(
        f"[{doc.metadata.get('source_id', 'unknown')}]\n{doc.page_content}"
        for doc in state["retrieved"]
    )

    # EXTEND: inject firm-specific instructions here (e.g. desk names, limits)
    user_prompt = f"""
Analyze the following capital market risk context.

Context:
{context}

Query focus: {state['query']}
"""

    response = llm.invoke(
        [
            HumanMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
    )

    text = response.content if hasattr(response, "content") else str(response)

    # Parse output sections
    # EXTEND: use Pydantic structured output (llm.with_structured_output)
    #         for more robust JSON extraction
    parts = text.split("JSON:", 1)
    draft_summary = parts[0].replace("SUMMARY:", "").strip()
    findings_json = parts[1].strip() if len(parts) > 1 else "[]"

    return {
        "draft_summary": draft_summary,
        "findings_json": findings_json,
        "messages": [AIMessage(content=draft_summary)],
    }

