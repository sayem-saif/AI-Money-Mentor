const form = document.getElementById("mentor-form");
const goalsList = document.getElementById("goals-list");
const addGoalBtn = document.getElementById("add-goal");
const loadingCard = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const loadingSteps = document.getElementById("loading-steps");
const results = document.getElementById("results");

const taxForm = document.getElementById("tax-form");
const taxResults = document.getElementById("tax-results");
const portfolioForm = document.getElementById("portfolio-form");
const portfolioResults = document.getElementById("portfolio-results");
const auditResults = document.getElementById("audit-results");
const refreshAuditBtn = document.getElementById("refresh-audit");
const addFundBtn = document.getElementById("add-fund");
const fundsList = document.getElementById("funds-list");
const recalculateBtn = document.getElementById("recalculate-btn");

let latestProfilePayload = null;

const loadingMessages = [
  "Profiling your finances...",
  "Calculating your FIRE number...",
  "Finding your blind spots...",
  "Generating your roadmap...",
];

const loadingStepLabels = [
  "Profiling Agent",
  "FIRE Calculator Agent",
  "Risk Gap Analyzer Agent",
  "Report Generator Agent",
];

function formatINR(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(number);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === tabId);
  });
}

document.querySelectorAll(".tab-btn").forEach((button) => {
  button.addEventListener("click", () => {
    switchTab(button.dataset.tab);
    if (button.dataset.tab === "tab-4") {
      loadAuditTrail();
    }
  });
});

function addGoalRow(goal = { name: "", target_amount: "", years: "" }) {
  const row = document.createElement("div");
  row.className = "goal-row";
  row.innerHTML = `
    <input type="text" placeholder="Goal Name" data-key="name" value="${escapeHtml(goal.name)}" required />
    <input type="number" placeholder="Target Amount ₹" data-key="target_amount" min="10000" value="${goal.target_amount}" required />
    <input type="number" placeholder="Years" data-key="years" min="1" max="40" value="${goal.years}" required />
    <button type="button" class="ghost-btn remove-goal">Remove</button>
  `;
  row.querySelector(".remove-goal").addEventListener("click", () => row.remove());
  goalsList.appendChild(row);
}

function addFundRow(fund = {}) {
  const wrap = document.createElement("div");
  wrap.className = "fund-row";
  wrap.innerHTML = `
    <div class="grid three">
      <label>Fund Name<input type="text" data-key="name" value="${escapeHtml(fund.name || "")}" required /></label>
      <label>Purchase Amount (₹)<input type="number" data-key="purchase_amount" value="${fund.purchase_amount || 0}" min="0" required /></label>
      <label>Current Value (₹)<input type="number" data-key="current_value" value="${fund.current_value || 0}" min="0" required /></label>
    </div>
    <div class="grid three">
      <label>Purchase Date<input type="date" data-key="purchase_date" value="${fund.purchase_date || ""}" required /></label>
      <label>Top Holding 1 (name %)<input type="text" data-key="holding_1" placeholder="Reliance 12" value="${escapeHtml(fund.holding_1 || "")}" /></label>
      <label>Top Holding 2 (name %)<input type="text" data-key="holding_2" placeholder="HDFC Bank 10" value="${escapeHtml(fund.holding_2 || "")}" /></label>
    </div>
    <div class="grid two">
      <label>Top Holding 3 (name %)<input type="text" data-key="holding_3" placeholder="Infosys 8" value="${escapeHtml(fund.holding_3 || "")}" /></label>
      <button type="button" class="ghost-btn remove-fund">Remove Fund</button>
    </div>
  `;
  wrap.querySelector(".remove-fund").addEventListener("click", () => wrap.remove());
  fundsList.appendChild(wrap);
}

function renderLoadingSteps(index) {
  loadingSteps.innerHTML = "";
  loadingStepLabels.forEach((label, idx) => {
    const li = document.createElement("li");
    li.textContent = idx <= index ? `[Done] ${label}` : `[Pending] ${label}`;
    li.className = idx <= index ? "done" : "pending";
    loadingSteps.appendChild(li);
  });
}

function startLoadingAnimation() {
  let idx = 0;
  loadingText.textContent = loadingMessages[0];
  renderLoadingSteps(0);
  return setInterval(() => {
    idx = (idx + 1) % loadingMessages.length;
    loadingText.textContent = loadingMessages[idx];
    renderLoadingSteps(idx);
  }, 1000);
}

function renderGauge(score) {
  const valueEl = document.getElementById("health-score-value");
  const ring = document.getElementById("gauge-value");
  const capped = Math.max(0, Math.min(100, Number(score || 0)));
  const circumference = 327;
  const offset = circumference - (capped / 100) * circumference;

  ring.style.strokeDashoffset = String(offset);
  ring.style.stroke = capped >= 70 ? "#00d4aa" : capped >= 40 ? "#ffb347" : "#ff6b6b";
  valueEl.textContent = String(capped);
}

function renderScoreBreakdown(breakdown) {
  const container = document.getElementById("score-breakdown");
  container.innerHTML = "";
  Object.entries(breakdown || {}).forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "score-row";
    row.innerHTML = `
      <label>${label} (${value})</label>
      <div class="bar"><span style="width:${Math.min(100, Number(value) * 5)}%"></span></div>
    `;
    container.appendChild(row);
  });
}

function renderResults(data) {
  renderGauge(data.health_score);
  renderScoreBreakdown(data.score_breakdown || {});

  const fire = data.fire_data || {};
  document.getElementById("fire-summary").innerHTML = `
    <p><strong>FIRE Number:</strong> ${fire.fire_number_inr || formatINR(fire.fire_number)}</p>
    <p><strong>Years to FIRE:</strong> ${fire.years_to_fire ?? "N/A"}</p>
    <p><strong>Total SIP Needed:</strong> ${fire.monthly_sip_needed_inr || formatINR(fire.monthly_sip_needed)}</p>
    <p><strong>Allocation:</strong> Equity ${fire.asset_allocation?.equity_percent ?? "-"}% | Debt ${fire.asset_allocation?.debt_percent ?? "-"}%</p>
  `;

  const goalsBody = document.getElementById("goals-table-body");
  goalsBody.innerHTML = "";
  (data.goals_sip || []).forEach((goal) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(goal.name)}</td>
      <td>${formatINR(goal.target_amount)}</td>
      <td>${goal.years}</td>
      <td>${goal.required_monthly_sip_inr || formatINR(goal.required_monthly_sip)}</td>
    `;
    goalsBody.appendChild(tr);
  });

  const gaps = document.getElementById("gap-cards");
  gaps.innerHTML = "";
  (data.gaps || []).forEach((gap) => {
    const level = String(gap.severity || "low").toLowerCase();
    const card = document.createElement("div");
    card.className = `gap-card gap-${level}`;
    card.innerHTML = `
      <h3>${escapeHtml(gap.gap_type)} (${escapeHtml(gap.severity)})</h3>
      <p><strong>Current:</strong> ${escapeHtml(gap.current_value)}</p>
      <p><strong>Recommended:</strong> ${escapeHtml(gap.recommended_value)}</p>
      <p>${escapeHtml(gap.action)}</p>
      <button class="ghost-btn">Learn How -></button>
    `;
    gaps.appendChild(card);
  });

  const actions = document.getElementById("priority-actions");
  actions.innerHTML = "";
  (data.priority_actions || []).forEach((action) => {
    const li = document.createElement("li");
    if (typeof action === "string") {
      li.textContent = action;
    } else if (action && typeof action === "object") {
      const label = action.priority ? `[${action.priority}] ` : "";
      li.textContent = `${label}${action.action || action.step || "Action item"}`;
    } else {
      li.textContent = String(action || "Action item");
    }
    actions.appendChild(li);
  });

  const roadmap = document.getElementById("roadmap");
  roadmap.innerHTML = "";
  (data.roadmap || []).forEach((item) => {
    const div = document.createElement("div");
    div.className = "road-item";
    div.innerHTML = `<strong>Month ${item.month}:</strong> ${escapeHtml(item.action)}`;
    roadmap.appendChild(div);
  });

  document.getElementById("summary-text").textContent = data.summary || "";
  document.getElementById("motivation-text").textContent = data.motivational_message || "";
}

function collectGoals() {
  const rows = [...goalsList.querySelectorAll(".goal-row")];
  return rows
    .map((row) => {
      const values = [...row.querySelectorAll("input")].reduce((acc, input) => {
        acc[input.dataset.key] = input.value;
        return acc;
      }, {});
      return {
        name: values.name,
        target_amount: Number(values.target_amount),
        years: Number(values.years),
      };
    })
    .filter((goal) => goal.name && goal.target_amount > 0 && goal.years > 0);
}

function collectFunds() {
  return [...fundsList.querySelectorAll(".fund-row")].map((row) => {
    const values = [...row.querySelectorAll("input")].reduce((acc, input) => {
      acc[input.dataset.key] = input.value;
      return acc;
    }, {});
    return {
      name: values.name,
      purchase_amount: Number(values.purchase_amount || 0),
      current_value: Number(values.current_value || 0),
      purchase_date: values.purchase_date,
      holding_1: values.holding_1 || "",
      holding_2: values.holding_2 || "",
      holding_3: values.holding_3 || "",
    };
  });
}

function updateSliderLabels() {
  const age = document.getElementById("slider-retirement-age");
  const returns = document.getElementById("slider-returns");
  const draw = document.getElementById("slider-draw");
  document.getElementById("slider-retirement-age-value").textContent = age.value;
  document.getElementById("slider-returns-value").textContent = returns.value;
  document.getElementById("slider-draw-value").textContent = Number(draw.value).toLocaleString("en-IN");
}

async function loadAuditTrail() {
  try {
    const response = await fetch("/api/audit-log");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not fetch audit logs.");
    }

    const logs = data.logs || [];
    auditResults.classList.remove("hidden");
    if (!logs.length) {
      auditResults.innerHTML = "<p>No audit entries yet.</p>";
      return;
    }

    auditResults.innerHTML = logs
      .map(
        (log) => `
      <div class="audit-row">
        <p><strong>${escapeHtml(log.timestamp)}</strong> · ${escapeHtml(log.endpoint)} · ${escapeHtml(log.status)}</p>
        <p>Result keys: ${(log.output_summary?.keys || []).join(", ")}</p>
      </div>
    `
      )
      .join("");
  } catch (error) {
    auditResults.classList.remove("hidden");
    auditResults.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = {
    name: formData.get("name"),
    age: Number(formData.get("age")),
    monthly_income: Number(formData.get("monthly_income")),
    monthly_expenses: Number(formData.get("monthly_expenses")),
    existing_savings: Number(formData.get("existing_savings")),
    existing_investments: Number(formData.get("existing_investments")),
    risk_appetite: formData.get("risk_appetite"),
    has_term_insurance: formData.get("has_term_insurance") === "true",
    has_health_insurance: formData.get("has_health_insurance") === "true",
    emergency_fund: Number(formData.get("emergency_fund")),
    goals: collectGoals(),
  };

  if (!payload.goals.length) {
    alert("Please add at least one financial goal.");
    return;
  }

  latestProfilePayload = payload;
  results.classList.add("hidden");
  loadingCard.classList.remove("hidden");
  const timer = startLoadingAnimation();

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Analysis failed.");
    }

    renderResults(data);
    results.classList.remove("hidden");
    results.scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    alert(error.message || "Something went wrong while analyzing your finances.");
  } finally {
    clearInterval(timer);
    loadingCard.classList.add("hidden");
  }
});

recalculateBtn.addEventListener("click", async () => {
  if (!latestProfilePayload) {
    alert("Run dashboard analysis first, then recalculate.");
    return;
  }
  try {
    const payload = {
      profile: latestProfilePayload,
      retirement_age: Number(document.getElementById("slider-retirement-age").value),
      expected_returns: Number(document.getElementById("slider-returns").value),
      target_monthly_corpus_draw: Number(document.getElementById("slider-draw").value),
    };
    const response = await fetch("/api/recalculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Recalculation failed.");
    }
    renderGauge(data.health_score);
    renderScoreBreakdown(data.score_breakdown || {});
    const fire = data.fire_data || {};
    document.getElementById("fire-summary").innerHTML = `
      <p><strong>FIRE Number:</strong> ${fire.fire_number_inr || formatINR(fire.fire_number)}</p>
      <p><strong>Years to FIRE:</strong> ${fire.years_to_fire ?? "N/A"}</p>
      <p><strong>Total SIP Needed:</strong> ${fire.monthly_sip_needed_inr || formatINR(fire.monthly_sip_needed)}</p>
      <p><strong>Assumptions:</strong> Retirement Age ${fire.assumptions?.retirement_age ?? "-"}, Returns ${fire.assumptions?.expected_returns ?? "-"}%</p>
    `;
  } catch (error) {
    alert(error.message || "Could not recalculate right now.");
  }
});

taxForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(taxForm);
  const payload = {
    annual_income: Number(formData.get("annual_income")),
    deductions_80c: Number(formData.get("deductions_80c") || 0),
    hra_exemption: Number(formData.get("hra_exemption") || 0),
    home_loan_interest: Number(formData.get("home_loan_interest") || 0),
  };

  try {
    const response = await fetch("/api/tax-wizard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Tax wizard failed.");
    }

    taxResults.classList.remove("hidden");
    taxResults.innerHTML = `
      <h3>Comparison Result</h3>
      <p><strong>Old Regime Tax:</strong> ${data.old_regime.tax_payable_inr}</p>
      <p><strong>New Regime Tax:</strong> ${data.new_regime.tax_payable_inr}</p>
      <p><strong>Recommended:</strong> ${String(data.recommended_regime || "").toUpperCase()} regime</p>
      <p><strong>Potential Tax Saved:</strong> ${data.tax_saved_inr}</p>
      <h4>Suggested Tax Plan</h4>
      <ul>${(data.tax_plan || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      <p class="section-disclaimer">Educational simulation only. Consult a SEBI-registered advisor for personalized advice.</p>
    `;
  } catch (error) {
    taxResults.classList.remove("hidden");
    taxResults.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
});

portfolioForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    funds: collectFunds(),
    regular_expense_ratio: Number(new FormData(portfolioForm).get("regular_expense_ratio") || 2.0),
    direct_expense_ratio: Number(new FormData(portfolioForm).get("direct_expense_ratio") || 1.5),
  };

  if (!payload.funds.length) {
    alert("Please add at least one fund.");
    return;
  }

  try {
    const response = await fetch("/api/portfolio-xray", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Portfolio x-ray failed.");
    }

    portfolioResults.classList.remove("hidden");
    portfolioResults.innerHTML = `
      <h3>XIRR</h3>
      <p><strong>${data.xirr_label}</strong></p>
      <h3>Overlap Matrix</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Fund A</th><th>Fund B</th><th>Overlap %</th><th>Shared Stocks</th></tr></thead>
          <tbody>
            ${(data.overlap_matrix || [])
              .map(
                (row) =>
                  `<tr><td>${escapeHtml(row.fund_a)}</td><td>${escapeHtml(row.fund_b)}</td><td>${row.overlap_percent}</td><td>${escapeHtml((row.shared_stocks || []).join(", "))}</td></tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
      <h3>Expense Ratio Impact</h3>
      <p>Regular annual cost: ${data.expense_analysis?.annual_cost_regular_inr || "-"}</p>
      <p>Direct annual cost: ${data.expense_analysis?.annual_cost_direct_inr || "-"}</p>
      <p>Annual savings: ${data.expense_analysis?.annual_savings_inr || "-"}</p>
      <p>10-year impact: ${data.expense_analysis?.ten_year_impact_inr || "-"}</p>
      <h3>Rebalancing Plan</h3>
      <ul>${(data.rebalancing_plan || [])
        .map(
          (item) =>
            `<li>${escapeHtml(item.fund)}: ${escapeHtml(item.action)}${item.wait_months_for_ltcg > 0 ? ` (wait ${item.wait_months_for_ltcg} months)` : ""}</li>`
        )
        .join("")}</ul>
      <h3>Specific Recommendations</h3>
      <ul>${(data.recommendations || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      <p class="section-disclaimer">Educational simulation only. Consult a SEBI-registered advisor for personalized advice.</p>
    `;
  } catch (error) {
    portfolioResults.classList.remove("hidden");
    portfolioResults.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
});

refreshAuditBtn.addEventListener("click", loadAuditTrail);
addGoalBtn.addEventListener("click", () => addGoalRow());
addFundBtn.addEventListener("click", () => addFundRow());

["slider-retirement-age", "slider-returns", "slider-draw"].forEach((id) => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener("input", updateSliderLabels);
  }
});

addGoalRow({ name: "Emergency Fund Top-up", target_amount: 270000, years: 1 });
addGoalRow({ name: "Retirement", target_amount: 30000000, years: 32 });

addFundRow({
  name: "Large Cap Fund",
  purchase_amount: 200000,
  current_value: 248000,
  purchase_date: "2023-06-15",
  holding_1: "Reliance 9",
  holding_2: "HDFC Bank 8",
  holding_3: "ICICI Bank 6",
});
addFundRow({
  name: "Flexi Cap Fund",
  purchase_amount: 180000,
  current_value: 220000,
  purchase_date: "2024-01-18",
  holding_1: "Reliance 7",
  holding_2: "Infosys 6",
  holding_3: "HDFC Bank 5",
});

updateSliderLabels();
