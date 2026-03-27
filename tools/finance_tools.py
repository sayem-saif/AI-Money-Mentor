import math
from datetime import date, datetime
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


def _old_regime_taxable_income(annual_income: float, deductions_80c: float, hra_exemption: float) -> float:
    standard_deduction = 50000.0
    taxable = annual_income - standard_deduction - min(150000.0, max(0.0, deductions_80c)) - max(0.0, hra_exemption)
    return max(0.0, taxable)


def _new_regime_taxable_income(annual_income: float) -> float:
    standard_deduction = 75000.0
    return max(0.0, annual_income - standard_deduction)


def _tax_from_slabs(taxable_income: float, slabs: List[Tuple[float, float]]) -> float:
    tax = 0.0
    previous_limit = 0.0
    for limit, rate in slabs:
        if taxable_income <= previous_limit:
            break
        slab_income = min(taxable_income, limit) - previous_limit
        if slab_income > 0:
            tax += slab_income * rate
        previous_limit = limit
    if taxable_income > previous_limit:
        tax += (taxable_income - previous_limit) * slabs[-1][1]
    return tax


def _apply_tax_rebate(taxable_income: float, tax: float, regime: str) -> float:
    if regime == "new" and taxable_income <= 700000:
        return 0.0
    if regime == "old" and taxable_income <= 500000:
        return 0.0
    return tax


def compare_tax_regimes(inputs: Dict[str, Any]) -> Dict[str, Any]:
    annual_income = max(0.0, safe_float(inputs.get("annual_income"), 0.0))
    deductions_80c = max(0.0, safe_float(inputs.get("deductions_80c"), 0.0))
    hra_exemption = max(0.0, safe_float(inputs.get("hra_exemption"), 0.0))
    home_loan_interest = max(0.0, safe_float(inputs.get("home_loan_interest"), 0.0))
    nps_contribution = max(0.0, min(50000.0, safe_float(inputs.get("nps_contribution"), 0.0)))
    city_type = (inputs.get("city_type") or "metro").lower()
    monthly_rent = max(0.0, safe_float(inputs.get("monthly_rent"), 0.0))
    
    # Calculate HRA more accurately based on city type and rent
    if monthly_rent > 0 and hra_exemption == 0:
        # HRA exemption = minimum of (i) actual HRA, (ii) 50% of basic (but we'll use 40-50% based on metro)
        # For Metro: typically 50%, Non-metro: 40%
        hra_percentage = 0.50 if city_type == "metro" else 0.40
        calculated_hra = min(monthly_rent * 12, annual_income * hra_percentage)
        hra_exemption = calculated_hra

    old_gross_income = annual_income
    old_hra = hra_exemption
    old_80c = min(deductions_80c, TAX_80C_LIMIT)
    old_nps = min(nps_contribution, 50000.0)
    old_standard_deduction = 75000.0
    old_home_loan = min(home_loan_interest, 200000.0)
    
    old_taxable = max(0.0, annual_income - old_hra - old_standard_deduction - old_80c - old_nps - old_home_loan)
    
    new_gross_income = annual_income
    new_nps = min(nps_contribution, 50000.0)
    new_standard_deduction = 75000.0
    new_taxable = max(0.0, annual_income - new_standard_deduction - new_nps)

    old_slabs = [(250000.0, 0.0), (500000.0, 0.05), (1000000.0, 0.2), (9999999999.0, 0.3)]
    new_slabs = [
        (300000.0, 0.0),
        (600000.0, 0.05),
        (900000.0, 0.1),
        (1200000.0, 0.15),
        (1500000.0, 0.2),
        (9999999999.0, 0.3),
    ]

    old_tax = _apply_tax_rebate(old_taxable, _tax_from_slabs(old_taxable, old_slabs), "old")
    new_tax = _apply_tax_rebate(new_taxable, _tax_from_slabs(new_taxable, new_slabs), "new")
    
    old_education_cess = old_tax * 0.04
    new_education_cess = new_tax * 0.04
    old_tax_with_cess = old_tax + old_education_cess
    new_tax_with_cess = new_tax + new_education_cess

    recommended_regime = "old" if old_tax_with_cess < new_tax_with_cess else "new"
    tax_saved = abs(old_tax_with_cess - new_tax_with_cess)

    plan = [
        "Max out 80C (ELSS/PPF/EPF) if staying in old regime.",
        "Use NPS additional deduction where applicable.",
        "Track HRA and home-loan documents in one place.",
        "Review regime choice at start of each financial year.",
    ]

    return {
        "inputs": {
            "annual_income": annual_income,
            "deductions_80c": deductions_80c,
            "hra_exemption": hra_exemption,
            "home_loan_interest": home_loan_interest,
            "nps_contribution": nps_contribution,
            "city_type": city_type,
            "monthly_rent": monthly_rent,
        },
        "old_regime": {
            "gross_income": round(old_gross_income, 2),
            "hra_exemption": round(old_hra, 2),
            "deductions_80c": round(old_80c, 2),
            "nps_contribution": round(old_nps, 2),
            "home_loan_interest": round(old_home_loan, 2),
            "taxable_income": round(old_taxable, 2),
            "tax_before_cess": round(old_tax, 2),
            "education_cess": round(old_education_cess, 2),
            "tax_payable": round(old_tax_with_cess, 2),
            "tax_payable_inr": format_inr(old_tax_with_cess),
        },
        "new_regime": {
            "gross_income": round(new_gross_income, 2),
            "nps_contribution": round(new_nps, 2),
            "taxable_income": round(new_taxable, 2),
            "tax_before_cess": round(new_tax, 2),
            "education_cess": round(new_education_cess, 2),
            "tax_payable": round(new_tax_with_cess, 2),
            "tax_payable_inr": format_inr(new_tax_with_cess),
        },
        "recommended_regime": recommended_regime,
        "tax_saved": round(tax_saved, 2),
        "tax_saved_inr": format_inr(tax_saved),
        "tax_plan": plan,
        "claimed_80d": False,
        "claimed_80g": False,
        "section_80c_suggestions": [
            "ELSS for tax + equity growth",
            "PPF for long-term safety",
            "EPF/VPF via payroll",
        ],
    }


def _parse_purchase_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return date.today()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _holding_period_months(start: date) -> int:
    today = date.today()
    return max(0, (today.year - start.year) * 12 + (today.month - start.month))


def _xirr(cashflows: List[Tuple[date, float]], guess: float = 0.12) -> float:
    if not cashflows:
        return 0.0
    start = min(d for d, _ in cashflows)

    def npv(rate: float) -> float:
        total = 0.0
        for dt, amount in cashflows:
            years = (dt - start).days / 365.0
            total += amount / ((1 + rate) ** years)
        return total

    rate = guess
    for _ in range(50):
        f_val = npv(rate)
        delta = 1e-5
        derivative = (npv(rate + delta) - f_val) / delta
        if abs(derivative) < 1e-9:
            break
        next_rate = rate - f_val / derivative
        if not math.isfinite(next_rate):
            break
        if abs(next_rate - rate) < 1e-7:
            rate = next_rate
            break
        rate = clamp(next_rate, -0.99, 5.0)
    return rate


def _extract_overlap_weights(text_items: List[str]) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    for raw in text_items:
        if not raw:
            continue
        parts = raw.strip().rsplit(" ", 1)
        if len(parts) == 2:
            name, pct = parts
            weight = safe_float(pct.replace("%", ""), 0.0)
            if weight > 0:
                weights[name.strip().lower()] = weight
    return weights


def portfolio_xray(inputs: Dict[str, Any]) -> Dict[str, Any]:
    funds = inputs.get("funds") or []
    parsed_funds: List[Dict[str, Any]] = []
    total_current = 0.0

    for item in funds:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "Fund").strip() or "Fund"
        purchase_amount = max(0.0, safe_float(item.get("purchase_amount"), 0.0))
        current_value = max(0.0, safe_float(item.get("current_value"), purchase_amount))
        purchase_date = _parse_purchase_date(item.get("purchase_date"))
        holdings_raw = [
            str(item.get("holding_1") or "").strip(),
            str(item.get("holding_2") or "").strip(),
            str(item.get("holding_3") or "").strip(),
        ]
        weights = _extract_overlap_weights(holdings_raw)

        total_current += current_value
        parsed_funds.append(
            {
                "name": name,
                "purchase_amount": purchase_amount,
                "current_value": current_value,
                "purchase_date": purchase_date,
                "holding_months": _holding_period_months(purchase_date),
                "weights": weights,
            }
        )

    cashflows: List[Tuple[date, float]] = []
    for fund in parsed_funds:
        cashflows.append((fund["purchase_date"], -fund["purchase_amount"]))
    cashflows.append((date.today(), total_current))
    xirr_value = _xirr(cashflows) if total_current > 0 else 0.0

    overlap_rows: List[Dict[str, Any]] = []
    for i in range(len(parsed_funds)):
        for j in range(i + 1, len(parsed_funds)):
            f1 = parsed_funds[i]
            f2 = parsed_funds[j]
            shared = set(f1["weights"].keys()) & set(f2["weights"].keys())
            overlap_pct = sum(min(f1["weights"][k], f2["weights"][k]) for k in shared)
            overlap_rows.append(
                {
                    "fund_a": f1["name"],
                    "fund_b": f2["name"],
                    "overlap_percent": round(overlap_pct, 2),
                    "shared_stocks": sorted(shared),
                }
            )

    regular_er = max(0.0, safe_float(inputs.get("regular_expense_ratio"), 2.0)) / 100
    direct_er = max(0.0, safe_float(inputs.get("direct_expense_ratio"), 1.5)) / 100
    annual_cost_regular = total_current * regular_er
    annual_cost_direct = total_current * direct_er
    annual_savings = max(0.0, annual_cost_regular - annual_cost_direct)
    ten_year_impact = annual_savings * (((1 + 0.12) ** 10 - 1) / 0.12) if annual_savings else 0.0

    rebalancing_plan: List[Dict[str, Any]] = []
    for fund in parsed_funds:
        wait_months = max(0, 12 - fund["holding_months"])
        action = "Hold" if wait_months > 0 else "Switch to lower overlap / direct plan"
        rebalancing_plan.append(
            {
                "fund": fund["name"],
                "holding_months": fund["holding_months"],
                "wait_months_for_ltcg": wait_months,
                "action": action,
            }
        )

    recommendations: List[str] = []
    for pair in sorted(overlap_rows, key=lambda x: x["overlap_percent"], reverse=True)[:3]:
        if pair["overlap_percent"] >= 20:
            recommendations.append(
                f"High overlap: {pair['fund_a']} vs {pair['fund_b']} ({pair['overlap_percent']}%). Consider one replacement."
            )
    if annual_savings > 0:
        recommendations.append(
            f"Switching to direct plans can save about {format_inr(annual_savings)} yearly."
        )
    if not recommendations:
        recommendations.append("Portfolio overlap and costs look healthy. Continue annual review.")

    return {
        "xirr": round(xirr_value * 100, 2),
        "xirr_label": f"{round(xirr_value * 100, 2)}%",
        "overlap_matrix": overlap_rows,
        "expense_analysis": {
            "regular_expense_ratio": round(regular_er * 100, 2),
            "direct_expense_ratio": round(direct_er * 100, 2),
            "annual_cost_regular": round(annual_cost_regular, 2),
            "annual_cost_regular_inr": format_inr(annual_cost_regular),
            "annual_cost_direct": round(annual_cost_direct, 2),
            "annual_cost_direct_inr": format_inr(annual_cost_direct),
            "annual_savings": round(annual_savings, 2),
            "annual_savings_inr": format_inr(annual_savings),
            "ten_year_impact": round(ten_year_impact, 2),
            "ten_year_impact_inr": format_inr(ten_year_impact),
        },
        "rebalancing_plan": rebalancing_plan,
        "recommendations": recommendations,
    }


def recalculate_fire_projection(
    profile: Dict[str, Any],
    retirement_age: float,
    expected_returns: float,
    target_monthly_corpus_draw: float,
) -> Dict[str, Any]:
    current_age = safe_float(profile.get("age"), 30)
    years_left = max(1.0, retirement_age - current_age)
    annual_expenses_target = max(100000.0, target_monthly_corpus_draw * 12)
    fire_number = annual_expenses_target * 25

    current_corpus = (
        safe_float(profile.get("existing_savings"))
        + safe_float(profile.get("existing_investments"))
        + safe_float(profile.get("emergency_fund"))
    )
    monthly_surplus = max(0.0, safe_float(profile.get("monthly_surplus")))
    annual_return = clamp(expected_returns / 100, 0.01, 0.25)
    months_to_fire = _estimate_fire_timeline_with_inflation(
        current_corpus,
        monthly_surplus,
        fire_number,
        annual_return,
        INFLATION_ANNUAL,
    )

    years_to_fire = (months_to_fire / 12) if math.isfinite(months_to_fire) else None
    sip_needed = _sip_payment_for_target(max(0.0, fire_number - current_corpus), int(years_left * 12), annual_return)

    return {
        "fire_number": round(fire_number, 2),
        "fire_number_inr": format_inr(fire_number),
        "years_to_fire": round(years_to_fire, 1) if years_to_fire is not None else None,
        "monthly_sip_needed": round(sip_needed, 2),
        "monthly_sip_needed_inr": format_inr(sip_needed),
        "assumptions": {
            "retirement_age": round(retirement_age, 1),
            "expected_returns": round(expected_returns, 2),
            "target_monthly_corpus_draw": round(target_monthly_corpus_draw, 2),
        },
    }


def compute_health_score_quick(profile: Dict[str, Any], fire_projection: Dict[str, Any]) -> Dict[str, Any]:
    monthly_income = max(1.0, safe_float(profile.get("monthly_income"), 1.0))
    monthly_expenses = safe_float(profile.get("monthly_expenses"), 0.0)
    emergency_fund = safe_float(profile.get("emergency_fund"), 0.0)
    emergency_target = monthly_expenses * 6
    emergency_score = int(round(clamp(emergency_fund / max(1.0, emergency_target), 0, 1) * 20))

    insurance_score = 0
    if bool(profile.get("has_term_insurance")):
        insurance_score += 10
    if bool(profile.get("has_health_insurance")):
        insurance_score += 10

    debt_health_score = 15 if monthly_expenses / monthly_income <= 0.5 else 8

    years_to_fire = fire_projection.get("years_to_fire")
    if years_to_fire is None:
        retirement_score = 4
    elif years_to_fire <= 20:
        retirement_score = 15
    elif years_to_fire <= 30:
        retirement_score = 11
    else:
        retirement_score = 7

    diversification_score = 15 if normalize_risk(profile.get("risk_appetite")) != "conservative" else 12
    tax_efficiency_score = 12

    breakdown = {
        "Emergency Preparedness": emergency_score,
        "Insurance Coverage": insurance_score,
        "Investment Diversification": diversification_score,
        "Debt Health": debt_health_score,
        "Tax Efficiency": tax_efficiency_score,
        "Retirement Readiness": retirement_score,
    }
    return {"health_score": sum(breakdown.values()), "score_breakdown": breakdown}
