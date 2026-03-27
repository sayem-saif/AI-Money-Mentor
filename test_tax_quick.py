"""
Quick test of Tax Wizard API endpoint
"""

import requests
import json

BASE_URL = "http://localhost:5000"

print("Testing /api/tax-wizard endpoint...")

tax_data = {
    "annual_income": 1800000,
    "deductions_80c": 150000,
    "hra_exemption": 360000,
    "home_loan_interest": 40000,
    "nps_contribution": 50000,
    "city_type": "metro",
    "monthly_rent": 30000
}

try:
    response = requests.post(f"{BASE_URL}/api/tax-wizard", json=tax_data, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse:\n{json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
