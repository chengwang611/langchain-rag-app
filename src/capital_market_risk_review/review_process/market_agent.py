"""Market Sensitivity Analysis Agent for review workflow."""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from .models import ReviewState


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SIMULATED_MARKET_DATA: dict[str, dict] = {
    "rates": {
        "10y_usd_swap_rate_pct": 4.52,
        "2s10s_spread_bps": 42,
        "move_index": 118.5,
        "daily_vol_pct": 0.80,
    },
    "credit": {
        "ig_cds_spread_bps": 68,
        "hy_cds_spread_bps": 342,
        "cva_market_factor": 1.15,
        "ig_daily_spread_vol_bps": 3.2,
    },
    "fx": {
        "usdcad_spot": 1.365,
        "fx_vol_1m_pct": 7.2,
        "daily_vol_pct": 0.45,
    },
    "equity": {
        "spx_level": 5_420,
        "vix": 18.4,
        "daily_vol_pct": 1.16,
    },
    "commodity": {
        "wti_crude_usd": 78.4,
        "daily_vol_pct": 2.10,
    },
}


@tool
def calculate_var_delta(
    asset_class: str,
    position_size_usd: float,
    confidence_level: float = 0.99,
    holding_period_days: int = 10,
) -> str:
    """Calculate VaR and Basel III capital charge for a position."""
    daily_vol_map = {
        "rates": 0.008,
        "credit": 0.015,
        "fx": 0.012,
        "equity": 0.018,
        "commodity": 0.022,
    }
    z_map = {0.99: 2.326, 0.95: 1.645, 0.975: 1.960}

    daily_vol = daily_vol_map.get(asset_class.lower(), 0.012)
    z_score = z_map.get(confidence_level, 2.326)

    var_1day_usd = position_size_usd * daily_vol * z_score
    var_nd_usd = var_1day_usd * (holding_period_days**0.5)
    basel_capital_charge = var_nd_usd * 3.0

    market_context = SIMULATED_MARKET_DATA.get(asset_class.lower(), {})

    return json.dumps(
        {
            "asset_class": asset_class,
            "position_size_usd": position_size_usd,
            "confidence_level": confidence_level,
            "holding_period_days": holding_period_days,
            "var_1day_usd": round(var_1day_usd, 2),
            "var_10day_usd": round(var_nd_usd, 2),
            "dv01_usd_per_bp": round(position_size_usd * 0.0001, 2)
            if asset_class.lower() == "rates"
            else None,
            "basel_iii_capital_charge_usd": round(basel_capital_charge, 2),
            "stressed_var_usd": round(var_nd_usd * 1.5, 2),
            "current_market_context": market_context,
            "regulation_ref": "Basel III IMA — BCBS 352",
        }
    )


@tool
def estimate_cva_exposure(
    counterparty_rating: str,
    product_type: str,
    notional_usd: float,
    maturity_years: float,
) -> str:
    """Estimate CVA exposure and capital charge under Basel III CVA framework."""
    pd_map = {
        "AAA": 0.001,
        "AA": 0.002,
        "A": 0.005,
        "BBB": 0.012,
        "BB": 0.030,
        "B": 0.070,
        "CCC": 0.150,
    }
    epe_factor_map = {
        "IRS": 0.020,
        "CDS": 0.050,
        "FX_Forward": 0.015,
        "Cross_Currency_Swap": 0.035,
        "Equity_Swap": 0.040,
        "Interest_Rate_Option": 0.025,
    }

    pd = pd_map.get(counterparty_rating.upper(), 0.020)
    lgd = 0.60
    epe_factor = epe_factor_map.get(product_type, 0.025)
    epe = notional_usd * epe_factor * (maturity_years**0.5)

    cva_market_factor = SIMULATED_MARKET_DATA["credit"]["cva_market_factor"]
    cva_base = pd * lgd * epe
    cva_market_adjusted = cva_base * cva_market_factor
    cva_capital_charge = cva_market_adjusted * 1.5

    return json.dumps(
        {
            "counterparty_rating": counterparty_rating,
            "product_type": product_type,
            "notional_usd": notional_usd,
            "maturity_years": maturity_years,
            "pd_assumption": pd,
            "lgd_assumption": lgd,
            "expected_positive_exposure_usd": round(epe, 2),
            "cva_base_usd": round(cva_base, 2),
            "cva_market_adjusted_usd": round(cva_market_adjusted, 2),
            "cva_capital_charge_usd": round(cva_capital_charge, 2),
            "market_spread_factor": cva_market_factor,
            "regulation_ref": "Basel III CVA Risk Framework — BCBS 325",
        }
    )


@tool
def calculate_rwa_impact(exposure_class: str, exposure_usd: float, risk_weight_pct: Optional[float] = None) -> str:
    """Calculate RWA impact and capital requirement under Basel III SA."""
    sa_risk_weights = {
        "corporate": 100.0,
        "sovereign": 0.0,
        "bank": 20.0,
        "retail": 75.0,
        "equity": 250.0,
        "securitisation": 1250.0,
        "mortgage": 35.0,
        "derivatives": 100.0,
        "other": 100.0,
    }

    rw = risk_weight_pct if risk_weight_pct is not None else sa_risk_weights.get(exposure_class.lower(), 100.0)

    rwa = exposure_usd * (rw / 100.0)
    min_capital = rwa * 0.080
    tier1_capital = rwa * 0.060
    ccb = rwa * 0.025
    total_requirement = rwa * 0.105

    return json.dumps(
        {
            "exposure_class": exposure_class,
            "exposure_usd": exposure_usd,
            "risk_weight_pct": rw,
            "rwa_usd": round(rwa, 2),
            "minimum_capital_requirement_usd": round(min_capital, 2),
            "tier1_capital_requirement_usd": round(tier1_capital, 2),
            "capital_conservation_buffer_usd": round(ccb, 2),
            "total_capital_requirement_usd": round(total_requirement, 2),
            "regulation_ref": "Basel III SA — BCBS 424 / CRR2",
        }
    )


_MARKET_TOOLS = [calculate_var_delta, estimate_cva_exposure, calculate_rwa_impact]
_market_llm = llm.bind_tools(_MARKET_TOOLS)
_tool_executor = {t.name: t for t in _MARKET_TOOLS}

MARKET_SYSTEM_PROMPT = """
You are the Market Sensitivity Analysis Agent for XXX Capital Markets.

Your role is to enrich each risk finding with quantitative market sensitivity metrics.

For findings in the JSON array:
- MARKET / rates exposure → call calculate_var_delta (asset_class="rates")
- COUNTERPARTY / CVA exposure → call estimate_cva_exposure
- Any finding with capital / RWA implications → call calculate_rwa_impact
- FX / equity exposure → call calculate_var_delta with appropriate asset_class

Use realistic XXX Capital Markets desk-size assumptions (e.g. $500M–$2B notional).

Produce a market sensitivity report with:
  MARKET SENSITIVITY SUMMARY:
  - VaR estimates per asset class with Basel III capital charges
  - CVA exposure estimates for counterparty findings
  - RWA impact and capital requirement estimates
  - Key market context (rates, spreads, volatility) at time of analysis
""".strip()


def market_sensitivity_agent_node(state: ReviewState) -> dict:
    """Enrich findings with VaR, CVA, and RWA estimates using tool calls."""
    findings_json = state.get("findings_json", "[]")
    compliance_report = state.get("compliance_report", "")

    messages: list = [
        HumanMessage(content=MARKET_SYSTEM_PROMPT),
        HumanMessage(content=(f"Risk findings:\n{findings_json}\n\n" f"Compliance context:\n{compliance_report}")),
    ]

    response = _market_llm.invoke(messages)
    for _ in range(12):
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            break

        for tc in response.tool_calls:
            tool_fn = _tool_executor.get(tc["name"])
            result = tool_fn.invoke(tc["args"]) if tool_fn else "Tool not found."
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        response = _market_llm.invoke(messages)

    market_report = response.content if hasattr(response, "content") else str(response)

    return {
        "market_sensitivity_report": market_report,
        "messages": [AIMessage(content=f"[Market Sensitivity Agent]\n{market_report}")],
    }
