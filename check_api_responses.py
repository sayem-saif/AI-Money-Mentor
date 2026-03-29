import requests

cases = [
    ("POST", "http://localhost:5000/api/tax", {}),
    (
        "POST",
        "http://localhost:5000/api/tax-wizard",
        {
            "annual_income": 1000000,
            "deductions_80c": 0,
            "hra_exemption": 0,
            "home_loan_interest": 0,
            "nps_contribution": 0,
            "city_type": "metro",
            "monthly_rent": 0,
        },
    ),
]

for method, url, payload in cases:
    try:
        resp = requests.request(method, url, json=payload, timeout=8)
        print("URL:", url)
        print("Status:", resp.status_code)
        print("Content-Type:", resp.headers.get("content-type", ""))
        print("Body:", resp.text[:220])
        print("-" * 60)
    except Exception as exc:
        print("URL:", url)
        print("ERROR:", str(exc))
        print("-" * 60)
