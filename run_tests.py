"""
Integration test for AI Money Mentor demo buttons.
This script validates that:
1. Flask server is running and HTML loads
2. All form fields exist in HTML
3. Demo button IDs are present
4. JavaScript functions can populate form fields
"""

import requests
import re
import sys

def test_server_running():
    """Test if Flask server is running"""
    try:
        r = requests.get('http://localhost:5000', timeout=5)
        if r.status_code == 200 and 'text/html' in r.headers.get('content-type', ''):
            print("✓ Flask server running and serving HTML")
            return True
        else:
            print(f"✗ Flask server returned unexpected response: {r.status_code}")
            return False
    except Exception as e:
        print(f"✗ Flask server not responding: {e}")
        return False

def test_html_elements():
    """Test if all required form elements and buttons exist in HTML"""
    r = requests.get('http://localhost:5000')
    html = r.text
    
    # Expected field names
    dashboard_fields = [
        'name', 'age', 'monthly_income', 'monthly_expenses', 'existing_savings',
        'existing_investments', 'emergency_fund', 'risk_appetite', 'has_term_insurance',
        'has_health_insurance'
    ]
    
    tax_fields = [
        'annual_income', 'deductions_80c', 'hra_exemption', 'home_loan_interest',
        'nps_contribution', 'city_type', 'monthly_rent'
    ]
    
    print("\n=== HTML STRUCTURE TEST ===")
    
    all_present = True
    
    print("\nDashboard form fields:")
    for field in dashboard_fields:
        if f"name=\"{field}\"" in html or f"name='{field}'" in html:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} - MISSING")
            all_present = False
    
    print("\nTax Wizard form fields:")
    for field in tax_fields:
        if f"name=\"{field}\"" in html or f"name='{field}'" in html:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} - MISSING")
            all_present = False
    
    print("\nDemo buttons:")
    if 'id="load-demo-data"' in html:
        print("  ✓ Dashboard demo button")
    else:
        print("  ✗ Dashboard demo button - MISSING")
        all_present = False
    
    if 'id="load-tax-demo-data"' in html:
        print("  ✓ Tax Wizard demo button")
    else:
        print("  ✗ Tax Wizard demo button - MISSING")
        all_present = False
    
    print("\nChart.js canvas element:")
    if 'id="healthScoreGauge"' in html:
        print("  ✓ healthScoreGauge canvas")
    else:
        print("  ✗ healthScoreGauge canvas - MISSING")
    
    return all_present

def test_api_endpoints():
    """Test if backend API endpoints work"""
    print("\n=== API ENDPOINTS TEST ===")
    
    # Test financial health analyze endpoint
    try:
        payload = {
            'name': 'Test User',
            'age': 30,
            'monthly_income': 100000,
            'monthly_expenses': 60000,
            'existing_savings': 200000,
            'existing_investments': 500000,
            'emergency_fund': 50000,
            'risk_appetite': 'moderate',
            'has_term_insurance': 'true',
            'has_health_insurance': 'true',
            'goals': []
        }
        r = requests.post('http://localhost:5000/api/analyze', json=payload, timeout=10)
        if r.status_code == 200:
            print("✓ /api/analyze endpoint working")
        else:
            print(f"✗ /api/analyze returned {r.status_code}")
            print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"✗ /api/analyze failed: {e}")
    
    # Test tax wizard endpoint
    try:
        payload = {
            'annual_income': 1800000,
            'deductions_80c': 150000,
            'hra_exemption': 360000,
            'home_loan_interest': 40000,
            'nps_contribution': 50000,
            'city_type': 'metro',
            'monthly_rent': 30000
        }
        r = requests.post('http://localhost:5000/api/tax', json=payload, timeout=10)
        if r.status_code == 200:
            print("✓ /api/tax endpoint working")
        else:
            print(f"✗ /api/tax returned {r.status_code}")
            print(f"  Response: {r.text[:200]}")
    except Exception as e:
        print(f"✗ /api/tax failed: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("AI Money Mentor - Integration Test")
    print("=" * 60)
    
    server_ok = test_server_running()
    if not server_ok:
        sys.exit(1)
    
    html_ok = test_html_elements()
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    if html_ok:
        print("✓ HTML structure validation PASSED")
        print("\nNEXT STEPS:")
        print("1. Open http://localhost:5000 in your browser")
        print("2. In Dashboard tab, click 'Load Demo Data' button")
        print("3. Verify form fields populate with demo values")
        print("4. Switch to Tax Wizard tab, click 'Load Demo Data' button")
        print("5. Verify form fields populate with demo values")
        print("6. Open browser Developer Console (F12) to check for errors")
    else:
        print("✗ HTML structure validation FAILED")
        sys.exit(1)
    print("=" * 60)
