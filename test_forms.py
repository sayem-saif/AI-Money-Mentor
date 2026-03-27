import re

with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Expected field names for Dashboard
dashboard_fields = [
    'name', 'age', 'monthly_income', 'monthly_expenses', 'existing_savings',
    'existing_investments', 'emergency_fund', 'risk_appetite', 'has_term_insurance',
    'has_health_insurance'
]

# Expected field names for Tax Wizard  
tax_fields = [
    'annual_income', 'deductions_80c', 'hra_exemption', 'home_loan_interest',
    'nps_contribution', 'city_type', 'monthly_rent'
]

print("=== DASHBOARD FORM FIELDS ===")
for field in dashboard_fields:
    if f"name='{field}'" in html:
        print(f"✓ {field} - FOUND")
    else:
        print(f"✗ {field} - MISSING")

print("\n=== TAX WIZARD FORM FIELDS ===")
for field in tax_fields:
    if f"name='{field}'" in html:
        print(f"✓ {field} - FOUND")
    else:
        print(f"✗ {field} - MISSING")

print("\n=== DEMO BUTTONS ===")
if 'id="load-demo-data"' in html:
    print("✓ Dashboard demo button - FOUND")
else:
    print("✗ Dashboard demo button - MISSING")

if 'id="load-tax-demo-data"' in html:
    print("✓ Tax Wizard demo button - FOUND")
else:
    print("✗ Tax Wizard demo button - MISSING")

print("\n=== GLOBAL VARIABLES ===")
with open("static/script.js", "r", encoding="utf-8") as f:
    js = f.read()

if "let goalsList =" in js or "const goalsList =" in js or "var goalsList =" in js:
    print("✓ goalsList variable initialized")
else:
    print("✗ goalsList variable NOT initialized")

