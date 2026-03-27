const form = document.getElementById("mentor-form");
const goalsList = document.getElementById("goals-list");
const addGoalBtn = document.getElementById("add-goal");
const loadingCard = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const results = document.getElementById("results");

const loadingMessages = [
  "Profiling your finances...",
  "Calculating your FIRE number...",
  "Finding your blind spots...",
  "Generating your roadmap...",
];

function formatINR(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(number);
}

function addGoalRow(goal = { name: "", target_amount: "", years: "" }) {
  const row = document.createElement("div");
  row.className = "goal-row";
  row.innerHTML = `
    <input type="text" placeholder="Goal Name" data-key="name" value="${goal.name}" required />
    <input type="number" placeholder="Target Amount ₹" data-key="target_amount" min="10000" value="${goal.target_amount}" required />
    <input type="number" placeholder="Years" data-key="years" min="1" max="40" value="${goal.years}" required />
    <button type="button" class="ghost-btn remove-goal">Remove</button>
  `;
  row.querySelector(".remove-goal").addEventListener("click", () => row.remove());
  goalsList.appendChild(row);
}

function startLoadingAnimation() {
  let idx = 0;
  loadingText.textContent = loadingMessages[0];
  return setInterval(() => {
    idx = (idx + 1) % loadingMessages.length;
    loadingText.textContent = loadingMessages[idx];
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
      <td>${goal.name}</td>
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
      <h3>${gap.gap_type} (${gap.severity})</h3>
      <p><strong>Current:</strong> ${gap.current_value}</p>
      <p><strong>Recommended:</strong> ${gap.recommended_value}</p>
      <p>${gap.action}</p>
    `;
    gaps.appendChild(card);
  });

  const actions = document.getElementById("priority-actions");
  actions.innerHTML = "";
  (data.priority_actions || []).forEach((action) => {
    const li = document.createElement("li");
    li.textContent = action;
    actions.appendChild(li);
  });

  const roadmap = document.getElementById("roadmap");
  roadmap.innerHTML = "";
  (data.roadmap || []).forEach((item) => {
    const div = document.createElement("div");
    div.className = "road-item";
    div.innerHTML = `<strong>Month ${item.month}:</strong> ${item.action}`;
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

addGoalBtn.addEventListener("click", () => addGoalRow());

addGoalRow({ name: "Emergency Fund Top-up", target_amount: 270000, years: 1 });
addGoalRow({ name: "Retirement", target_amount: 30000000, years: 32 });
