import math
from typing import Any, Dict, List, Tuple

EQUITY_RETURN_ANNUAL = 0.12
DEBT_RETURN_ANNUAL = 0.07
INFLATION_ANNUAL = 0.06
TAX_80C_LIMIT = 150000


def format_inr(value: float) -> str:
    rounded = int(round(value))
    sign = "-" if rounded < 0 else ""
    n = str(abs(rounded))
    if len(n) <= 3:
        return f"{sign}₹{n}"
    last3 = n[-3:]
    rest = n[:-3]
    chunks: List[str] = []
    while len(rest) > 2:
        chunks.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        chunks.insert(0, rest)
    return f"{sign}₹{','.join(chunks)},{last3}"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def normalize_risk(risk: str) -> str:
    value = (risk or "moderate").strip().lower()
    mapping = {
        "conservative": "conservative",
        "low": "conservative",
        "moderate": "moderate",
        "medium": "moderate",
        "aggressive": "aggressive",
        "high": "aggressive",
    }
    return mapping.get(value, "moderate")


def _annual_rate_from_risk(risk: str) -> float:
    profile_rate = {
        "conservative": 0.08,
        "moderate": 0.10,
        "aggressive": 0.12,
    }
    return profile_rate[normalize_risk(risk)]


def _sip_payment_for_target(target_amount: float, months: int, annual_return: float) -> float:
    if months <= 0:
        return max(0.0, target_amount)
    if target_amount <= 0:
        return 0.0
    monthly_rate = annual_return / 12
    if monthly_rate <= 0:
        return target_amount / months
    factor = (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    return target_amount / factor if factor else target_amount / months


def _estimate_months_to_target(
    principal: float,
    monthly_contribution: float,
    target: float,
    annual_return: float,
) -> float:
    if target <= principal:
        return 0.0
    r = annual_return / 12
    if monthly_contribution <= 0 and r <= 0:
        return float("inf")
    if r <= 0:
        if monthly_contribution <= 0:
            return float("inf")
        return (target - principal) / monthly_contribution

    if monthly_contribution <= 0:
        if principal <= 0:
            return float("inf")
        return math.log(target / principal) / math.log(1 + r)

    numerator = target * r + monthly_contribution
    denominator = principal * r + monthly_contribution
    if numerator <= 0 or denominator <= 0:
        return float("inf")
    months = math.log(numerator / denominator) / math.log(1 + r)
    return max(0.0, months)


def _estimate_fire_timeline_with_inflation(
    principal: float,
    monthly_contribution: float,
    initial_fire_target: float,
    annual_return: float,
    annual_inflation: float,
    max_months: int = 80 * 12,
) -> float:
    if principal >= initial_fire_target:
        return 0.0

    monthly_growth = annual_return / 12
    monthly_inflation = annual_inflation / 12
    corpus = max(0.0, principal)
    fire_target = max(1.0, initial_fire_target)

    for month in range(1, max_months + 1):
        corpus = corpus * (1 + monthly_growth) + monthly_contribution
        fire_target = fire_target * (1 + monthly_inflation)
        if corpus >= fire_target:
            return float(month)

    return float("inf")


def _blended_return_by_age(age: float) -> Tuple[float, float, float]:
    equity_pct = clamp(100 - age, 10, 90)
    debt_pct = 100 - equity_pct
    blended = (equity_pct / 100) * EQUITY_RETURN_ANNUAL + (debt_pct / 100) * DEBT_RETURN_ANNUAL
    return equity_pct, debt_pct, blended


def validate_and_structure_profile(user_data: Dict[str, Any]) -> Dict[str, Any]:
    age = int(clamp(safe_float(user_data.get("age"), 30), 18, 75))
    monthly_income = max(15000.0, safe_float(user_data.get("monthly_income"), 60000.0))
    monthly_expenses = max(5000.0, safe_float(user_data.get("monthly_expenses"), monthly_income * 0.6))
    existing_savings = max(0.0, safe_float(user_data.get("existing_savings"), 0.0))
    existing_investments = max(0.0, safe_float(user_data.get("existing_investments"), 0.0))
    emergency_fund = max(0.0, safe_float(user_data.get("emergency_fund"), 0.0))
    risk_appetite = normalize_risk(user_data.get("risk_appetite", "moderate"))

    goals: List[Dict[str, Any]] = []
    raw_goals = user_data.get("goals") or []
    for raw_goal in raw_goals:
        if not isinstance(raw_goal, dict):
            continue
        name = str(raw_goal.get("name") or "Unnamed Goal").strip() or "Unnamed Goal"
        target_amount = max(10000.0, safe_float(raw_goal.get("target_amount"), 100000.0))
        years = max(1, int(clamp(safe_float(raw_goal.get("years"), 5), 1, 40)))
        goals.append({
            "name": name,
            "target_amount": target_amount,
            "years": years,
        })

    if not goals:
        goals = [
            {"name": "Emergency Fund", "target_amount": monthly_expenses * 6, "years": 1},
            {"name": "Retirement", "target_amount": monthly_expenses * 12 * 25, "years": max(5, 60 - age)},
        ]

    profile = {
        "name": str(user_data.get("name") or "User").strip() or "User",
        "age": age,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "existing_savings": existing_savings,
        "existing_investments": existing_investments,
        "emergency_fund": emergency_fund,
        "risk_appetite": risk_appetite,
        "goals": goals,
        "has_term_insurance": bool(user_data.get("has_term_insurance", False)),
        "has_health_insurance": bool(user_data.get("has_health_insurance", False)),
        "monthly_surplus": max(0.0, monthly_income - monthly_expenses),
    }
    return profile


def calculate_fire_metrics(profile: Dict[str, Any]) -> Dict[str, Any]:
    monthly_income = safe_float(profile.get("monthly_income"))
    monthly_expenses = safe_float(profile.get("monthly_expenses"))
    annual_expenses = monthly_expenses * 12
    fire_number = annual_expenses * 25

    equity_pct, debt_pct, blended_return = _blended_return_by_age(safe_float(profile.get("age"), 30))
    monthly_surplus = max(0.0, safe_float(profile.get("monthly_surplus"), monthly_income - monthly_expenses))
    current_corpus = (
        safe_float(profile.get("existing_savings"))
        + safe_float(profile.get("existing_investments"))
        + safe_float(profile.get("emergency_fund"))
    )

    months_to_fire = _estimate_fire_timeline_with_inflation(
        current_corpus,
        monthly_surplus,
        fire_number,
        blended_return,
        INFLATION_ANNUAL,
    )
    years_to_fire = (months_to_fire / 12) if math.isfinite(months_to_fire) else None

    goals_sip: List[Dict[str, Any]] = []
    total_goal_sip = 0.0
    for goal in profile.get("goals", []):
        years = int(safe_float(goal.get("years"), 1))
        months = max(1, years * 12)
        target = safe_float(goal.get("target_amount"), 0.0)
        annual_return = _annual_rate_from_risk(profile.get("risk_appetite", "moderate"))
        sip = _sip_payment_for_target(target, months, annual_return)
        total_goal_sip += sip
        goals_sip.append(
            {
                "name": goal.get("name", "Goal"),
                "target_amount": round(target, 2),
                "years": years,
                "required_monthly_sip": round(sip, 2),
                "required_monthly_sip_inr": format_inr(sip),
            }
        )

    emergency_target = monthly_expenses * 6
    emergency_gap = max(0.0, emergency_target - safe_float(profile.get("emergency_fund")))

    milestones: List[Dict[str, Any]] = []
    running_corpus = current_corpus
    monthly_r = blended_return / 12
    monthly_contribution = monthly_surplus
    for month in range(1, 13):
        running_corpus = running_corpus * (1 + monthly_r) + monthly_contribution
        milestones.append(
            {
                "month": month,
                "projected_corpus": round(running_corpus, 2),
                "projected_corpus_inr": format_inr(running_corpus),
            }
        )

    return {
        "fire_number": round(fire_number, 2),
        "fire_number_inr": format_inr(fire_number),
        "annual_expenses": round(annual_expenses, 2),
        "monthly_surplus": round(monthly_surplus, 2),
        "monthly_surplus_inr": format_inr(monthly_surplus),
        "years_to_fire": round(years_to_fire, 1) if years_to_fire is not None else None,
        "asset_allocation": {
            "equity_percent": round(equity_pct, 1),
            "debt_percent": round(debt_pct, 1),
        },
        "assumptions": {
            "equity_return_annual": EQUITY_RETURN_ANNUAL,
            "debt_return_annual": DEBT_RETURN_ANNUAL,
            "inflation_annual": INFLATION_ANNUAL,
            "real_return_annual": round((1 + blended_return) / (1 + INFLATION_ANNUAL) - 1, 4),
        },
        "goals_sip": goals_sip,
        "total_required_monthly_sip": round(total_goal_sip, 2),
        "total_required_monthly_sip_inr": format_inr(total_goal_sip),
        "emergency_fund_target": round(emergency_target, 2),
        "emergency_fund_target_inr": format_inr(emergency_target),
        "emergency_fund_gap": round(emergency_gap, 2),
        "emergency_fund_gap_inr": format_inr(emergency_gap),
        "milestone_12_months": milestones,
    }


def analyze_financial_gaps(profile: Dict[str, Any], fire_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []

    annual_income = safe_float(profile.get("monthly_income")) * 12
    required_term_cover = annual_income * 10
    has_term = bool(profile.get("has_term_insurance"))
    if not has_term:
        gaps.append(
            {
                "gap_type": "Term Insurance",
                "severity": "high",
                "current_value": "No term insurance",
                "recommended_value": format_inr(required_term_cover),
                "action": "Buy a pure term plan with at least 10x annual income cover.",
            }
        )

    has_health = bool(profile.get("has_health_insurance"))
    if not has_health:
        gaps.append(
            {
                "gap_type": "Health Insurance",
                "severity": "high",
                "current_value": "Not covered",
                "recommended_value": "Family floater policy with adequate sum insured",
                "action": "Purchase health insurance immediately to protect savings from medical shocks.",
            }
        )

    emergency_target = safe_float(fire_data.get("emergency_fund_target"))
    emergency_current = safe_float(profile.get("emergency_fund"))
    if emergency_current < emergency_target:
        gaps.append(
            {
                "gap_type": "Emergency Fund",
                "severity": "high" if emergency_current < (emergency_target * 0.5) else "medium",
                "current_value": format_inr(emergency_current),
                "recommended_value": format_inr(emergency_target),
                "action": "Build emergency corpus in liquid fund or high-yield savings over next 6-9 months.",
            }
        )

    expenses_ratio = safe_float(profile.get("monthly_expenses")) / max(1.0, safe_float(profile.get("monthly_income")))
    if expenses_ratio > 0.5:
        gaps.append(
            {
                "gap_type": "Debt/Spending Health",
                "severity": "medium" if expenses_ratio <= 0.7 else "high",
                "current_value": f"{round(expenses_ratio * 100, 1)}% of income used in expenses",
                "recommended_value": "Keep expenses <= 50% of income",
                "action": "Trim discretionary costs and redirect at least 20% income to investments.",
            }
        )

    invested_80c = min(TAX_80C_LIMIT, safe_float(profile.get("existing_investments")) * 0.1)
    tax_gap = max(0.0, TAX_80C_LIMIT - invested_80c)
    if tax_gap > 0:
        gaps.append(
            {
                "gap_type": "Tax Saving (80C)",
                "severity": "low" if tax_gap < 50000 else "medium",
                "current_value": format_inr(invested_80c),
                "recommended_value": format_inr(TAX_80C_LIMIT),
                "action": f"Invest additional {format_inr(tax_gap)} via ELSS, PPF, or EPF to optimize taxes.",
            }
        )

    years_to_fire = fire_data.get("years_to_fire")
    monthly_surplus = safe_float(profile.get("monthly_surplus"))
    required_sip = safe_float(fire_data.get("total_required_monthly_sip"))

    if required_sip > monthly_surplus and required_sip > 0:
        gaps.append(
            {
                "gap_type": "Retirement Readiness",
                "severity": "high",
                "current_value": f"Required SIP {format_inr(required_sip)} exceeds surplus {format_inr(monthly_surplus)}",
                "recommended_value": "Monthly surplus should exceed required SIP",
                "action": "Increase income, reduce expenses, or extend goal timelines so SIP is affordable.",
            }
        )
    elif years_to_fire is None:
        gaps.append(
            {
                "gap_type": "Retirement Readiness",
                "severity": "high",
                "current_value": "Current surplus insufficient for FIRE",
                "recommended_value": "Increase monthly investing and reduce expenses",
                "action": "Raise SIP contribution by increasing income and setting strict spending caps.",
            }
        )
    elif years_to_fire > 35:
        gaps.append(
            {
                "gap_type": "Retirement Readiness",
                "severity": "medium",
                "current_value": f"Estimated FIRE in {years_to_fire} years",
                "recommended_value": "FIRE timeline below 30 years",
                "action": "Step up SIP by 10-15% annually and maintain equity exposure as per risk profile.",
            }
        )

    return gaps


def _score_breakdown(profile: Dict[str, Any], fire_data: Dict[str, Any], gaps: List[Dict[str, Any]]) -> Dict[str, int]:
    monthly_expenses = safe_float(profile.get("monthly_expenses"))
    emergency_target = monthly_expenses * 6
    emergency_current = safe_float(profile.get("emergency_fund"))
    emergency_ratio = emergency_current / emergency_target if emergency_target else 1
    emergency_score = int(round(clamp(emergency_ratio, 0, 1) * 20))

    insurance_score = 0
    if profile.get("has_term_insurance"):
        insurance_score += 10
    if profile.get("has_health_insurance"):
        insurance_score += 10

    equity_pct = safe_float(fire_data.get("asset_allocation", {}).get("equity_percent"), 50)
    diversification_score = 15 if 30 <= equity_pct <= 80 else 10

    expense_ratio = monthly_expenses / max(1.0, safe_float(profile.get("monthly_income")))
    debt_health_score = 15 if expense_ratio <= 0.5 else (10 if expense_ratio <= 0.65 else 5)

    tax_gaps = [gap for gap in gaps if gap.get("gap_type") == "Tax Saving (80C)"]
    tax_efficiency_score = 15 if not tax_gaps else 8

    years_to_fire = fire_data.get("years_to_fire")
    monthly_surplus = max(1.0, safe_float(profile.get("monthly_surplus")))
    required_sip = safe_float(fire_data.get("total_required_monthly_sip"))
    sip_burden_ratio = required_sip / monthly_surplus

    if sip_burden_ratio > 1.5:
        retirement_score = 4
    elif sip_burden_ratio > 1.1:
        retirement_score = 7
    elif years_to_fire is None:
        retirement_score = 4
    elif years_to_fire <= 25:
        retirement_score = 12
    elif years_to_fire <= 30:
        retirement_score = 10
    elif years_to_fire <= 35:
        retirement_score = 8
    else:
        retirement_score = 6

    return {
        "Emergency Preparedness": emergency_score,
        "Insurance Coverage": insurance_score,
        "Investment Diversification": diversification_score,
        "Debt Health": debt_health_score,
        "Tax Efficiency": tax_efficiency_score,
        "Retirement Readiness": retirement_score,
    }


def build_final_report(
    profile: Dict[str, Any],
    fire_data: Dict[str, Any],
    gaps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    score_breakdown = _score_breakdown(profile, fire_data, gaps)
    health_score = sum(score_breakdown.values())

    sorted_gaps = sorted(
        gaps,
        key=lambda item: {"high": 0, "medium": 1, "low": 2}.get(item.get("severity", "low"), 3),
    )

    priority_actions: List[str] = [gap.get("action", "") for gap in sorted_gaps if gap.get("action")][:5]
    if len(priority_actions) < 5:
        fallback_actions = [
            "Automate SIP on salary day to improve consistency.",
            "Review investment portfolio quarterly and rebalance.",
            "Increase SIP by 10% every year (step-up SIP).",
            "Track expenses weekly to keep lifestyle inflation in check.",
            "Maintain separate buckets for goals and avoid early withdrawals.",
        ]
        for action in fallback_actions:
            if len(priority_actions) >= 5:
                break
            if action not in priority_actions:
                priority_actions.append(action)

    roadmap: List[Dict[str, Any]] = []
    base_month_actions = [
        "Buy or top up term and health insurance coverage.",
        "Start/boost emergency fund in liquid instruments.",
        "Set up SIPs for all goals based on monthly plan.",
        "Optimize 80C investments using ELSS/PPF mix.",
        "Cut non-essential expenses and lock savings rate.",
        "Review and rebalance equity-debt allocation.",
        "Increase SIP by 5% with income growth.",
        "Create debt repayment plan for costly liabilities.",
        "Run a tax and cashflow mid-year review.",
        "Check progress against FIRE milestone.",
        "Boost retirement corpus with annual bonus.",
        "Do annual financial health reset and set next-year goals.",
    ]
    for idx, action in enumerate(base_month_actions, start=1):
        roadmap.append({"month": idx, "action": action})

    summary = (
        f"{profile.get('name', 'You')} currently earns {format_inr(profile.get('monthly_income', 0))} per month "
        f"with expenses of {format_inr(profile.get('monthly_expenses', 0))}. "
        f"Your estimated Money Health Score is {health_score}/100. "
        f"With disciplined SIP investing, your FIRE target of {fire_data.get('fire_number_inr')} "
        f"can be reached in about {fire_data.get('years_to_fire', 'N/A')} years."
    )

    return {
        "health_score": health_score,
        "score_breakdown": score_breakdown,
        "fire_data": {
            "fire_number": fire_data.get("fire_number"),
            "fire_number_inr": fire_data.get("fire_number_inr"),
            "years_to_fire": fire_data.get("years_to_fire"),
            "monthly_sip_needed": fire_data.get("total_required_monthly_sip"),
            "monthly_sip_needed_inr": fire_data.get("total_required_monthly_sip_inr"),
            "asset_allocation": fire_data.get("asset_allocation"),
            "milestones": fire_data.get("milestone_12_months"),
        },
        "goals_sip": fire_data.get("goals_sip", []),
        "gaps": sorted_gaps,
        "roadmap": roadmap,
        "priority_actions": priority_actions,
        "summary": summary,
        "motivational_message": "Aap disciplined SIP aur smart tax planning se next level wealth build kar sakte ho. Har mahine ek small step, long term me huge difference banata hai.",
    }
