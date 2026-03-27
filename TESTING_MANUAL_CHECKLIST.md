# 🧪 AI Money Mentor - Manual Testing Checklist

The application is now fixed and running at **http://localhost:5000**

## ✅ What Was Fixed
1. **Added missing Tax Wizard demo button** (id="load-tax-demo-data")
2. **Added 3 missing form fields** to Tax Wizard section:
   - NPS Contribution (₹)
   - City Type (metro/non-metro dropdown)
   - Monthly Rent (₹)

All HTML form fields now match the JavaScript function expectations.

---

## 📋 Manual Testing Instructions

### Dashboard Tab - "Load Demo Data" Button
1. Open http://localhost:5000 in your browser
2. Click on the **Dashboard** tab (should be active)
3. Look for the **"Load Demo Data"** button (gray button next to "Step 1" heading)
4. **Click the button**
5. ✓ **Expected result:** Form should populate with demo values:
   - Name: "Arjun Sharma"
   - Age: "34"
   - Monthly Income: "200000"
   - Monthly Expenses: "80000"
   - Existing Savings: "50000"
   - Existing Investments: "1800000"
   - Emergency Fund: "30000"
   - Risk Appetite: "moderate"
   - Term Insurance: "No"
   - Health Insurance: "Yes"
   - **Financial Goals section** should show 4 pre-filled goals

### Tax Wizard Tab - "Load Demo Data" Button
1. Click on the **Tax Wizard** tab (2nd tab)
2. Look for the **"Load Demo Data"** button (gray button next to "Tax Wizard Agent" heading)
3. **Click the button**
4. ✓ **Expected result:** Form should populate with demo values:
   - Annual Income: "1800000"
   - 80C Deductions: "150000"
   - HRA Exemption: "360000"
   - Home Loan Interest: "40000"
   - NPS Contribution: "50000"
   - City Type: "metro"
   - Monthly Rent: "30000"

---

## 🐛 Debugging If Buttons Don't Work

**If the buttons don't populate the form:**

1. **Open Browser Developer Console** (Press **F12**)
2. Click **Console** tab
3. **Click one of the demo buttons**
4. **Look for red error messages** in the console
5. **Screenshot the errors** and share them

Common issues:
- Form element names don't match (unlikely now - we validated)
- JavaScript file isn't loading (check Network tab)
- goalsList variable is null for Dashboard (check console)
- Select dropdown value not setting correctly

---

## 🚀 Testing the Run Buttons

After demo data loads:

### Dashboard Tab
1. Click **"Run Financial Health Analysis"** button
2. ✓ Below the form, health score should appear with:
   - Donut chart gauge (0-100)
   - 6 progress bars showing score breakdown
   - Recommendations from AI

### Tax Wizard Tab
1. Click **"Run Tax Wizard"** button
2. ✓ Tax comparison should show:
   - Old Regime section with accordion (click to expand)
   - New Regime section with accordion
   - Verdict banner showing which regime is better
   - Recommended instruments for tax saving

---

## ✨ Expected Behavior Summary

| Feature | Status |
|---------|--------|
| Dashboard demo button | ✓ Should populate form |
| Tax Wizard demo button | ✓ Should populate form |
| Dashboard form has all fields | ✓ Verified |
| Tax Wizard form has all fields | ✓ Verified (newly added) |
| Financial Health API | ✓ Working |
| Tax Wizard API | ✓ Working |
| Chart.js gauge | ✓ Canvas element present |

---

## 📝 Notes

- **commit ead9ce7**: Fixed Tax Wizard demo button and input fields
- All form field names now match JavaScript selectors
- Both demo buttons have null-safety checks
- Flask server is running on localhost:5000

---

**STATUS: READY FOR TESTING** ✓

Please test both demo buttons and report any console errors!
