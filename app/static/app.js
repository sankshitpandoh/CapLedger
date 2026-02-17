const state = {
  asOf: new Date().toISOString().slice(0, 10),
  currentScreen: "dashboard",
  employees: [],
  grants: [],
  dashboard: null,
  employeeSearch: "",
  employeeStatus: "all",
  grantSearch: "",
  selectedExerciseGrantId: null,
  exerciseHistory: [],
  auth: {
    authenticated: false,
    role: null,
    full_name: "",
    email: "",
    employee_id: null,
  },
  allowedScreens: ["dashboard"],
};

const screenMeta = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Real-time ESOP metrics and vesting position.",
  },
  employees: {
    title: "Employees",
    subtitle: "Onboard, track, and search your cap-table participants.",
  },
  grants: {
    title: "Grants",
    subtitle: "Create grants and monitor vesting availability across the organization.",
  },
  exercises: {
    title: "Exercises",
    subtitle: "Review option exercise history and availability.",
  },
};

const els = {
  authGate: document.getElementById("authGate"),
  appShell: document.getElementById("appShell"),
  workspaceSubtitle: document.getElementById("workspaceSubtitle"),
  currentUserName: document.getElementById("currentUserName"),
  currentUserMeta: document.getElementById("currentUserMeta"),
  logoutBtn: document.getElementById("logoutBtn"),
  poolPanel: document.getElementById("poolPanel"),
  toast: document.getElementById("toast"),
  navButtons: document.getElementById("navButtons"),
  screenTitle: document.getElementById("screenTitle"),
  screenSubtitle: document.getElementById("screenSubtitle"),
  asOfDate: document.getElementById("asOfDate"),
  refreshDataBtn: document.getElementById("refreshDataBtn"),
  metricsGrid: document.getElementById("metricsGrid"),
  poolText: document.getElementById("poolText"),
  poolProgressBar: document.getElementById("poolProgressBar"),
  dashboardGrantTableBody: document.getElementById("dashboardGrantTableBody"),
  employeeForm: document.getElementById("employeeForm"),
  employeeMessage: document.getElementById("employeeMessage"),
  employeeSearch: document.getElementById("employeeSearch"),
  employeeStatusFilter: document.getElementById("employeeStatusFilter"),
  employeeCountText: document.getElementById("employeeCountText"),
  employeesTableBody: document.getElementById("employeesTableBody"),
  grantForm: document.getElementById("grantForm"),
  grantMessage: document.getElementById("grantMessage"),
  grantEmployeeSelect: document.getElementById("grantEmployeeSelect"),
  grantSearch: document.getElementById("grantSearch"),
  grantCountText: document.getElementById("grantCountText"),
  grantsTableBody: document.getElementById("grantsTableBody"),
  exerciseForm: document.getElementById("exerciseForm"),
  exerciseMessage: document.getElementById("exerciseMessage"),
  exerciseGrantSelect: document.getElementById("exerciseGrantSelect"),
  exerciseHistoryGrantSelect: document.getElementById("exerciseHistoryGrantSelect"),
  exerciseGrantSummary: document.getElementById("exerciseGrantSummary"),
  exerciseTableBody: document.getElementById("exerciseTableBody"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (response.status === 401) {
    state.auth.authenticated = false;
    renderAuthGate();
    throw new Error("Session expired. Please sign in again.");
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function fetchAllPaginated(path, pageSize = 200) {
  const results = [];
  let offset = 0;

  while (true) {
    const page = await api(`${path}?limit=${pageSize}&offset=${offset}`);
    results.push(...page);
    if (page.length < pageSize) {
      break;
    }
    offset += pageSize;
  }

  return results;
}

function formatInt(value) {
  return Number(value || 0).toLocaleString();
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    const [year, month, day] = value.slice(0, 10).split("-");
    return `${month}/${day}/${year}`;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }
  return parsed.toLocaleDateString();
}

function formatMoneyFromCents(value) {
  return `$${(Number(value || 0) / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function dollarsToCents(raw) {
  if (raw === "" || raw === null || raw === undefined) {
    return null;
  }
  return Math.round(parseFloat(raw) * 100);
}

function showToast(message, kind = "success") {
  els.toast.textContent = message;
  els.toast.className = `toast show ${kind === "error" ? "error" : ""}`;
  window.clearTimeout(showToast._timer);
  showToast._timer = window.setTimeout(() => {
    els.toast.className = "toast";
  }, 2200);
}

function setMessage(el, message, ok) {
  el.textContent = message;
  el.className = `message ${ok ? "success" : "error"}`;
}

function clearMessage(el) {
  el.textContent = "";
  el.className = "message";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getEmployeeById(employeeId) {
  return state.employees.find((employee) => employee.id === employeeId) || null;
}

function getSummaryByGrantId(grantId) {
  if (!state.dashboard) {
    return null;
  }
  return state.dashboard.grant_summaries.find((summary) => summary.grant_id === grantId) || null;
}

function normalizeScreen(screen) {
  if (!screenMeta[screen]) {
    return "dashboard";
  }

  if (!state.allowedScreens.includes(screen)) {
    return "dashboard";
  }

  return screen;
}

function setScreen(screen) {
  const normalized = normalizeScreen(screen);
  state.currentScreen = normalized;

  document.querySelectorAll(".screen").forEach((section) => {
    const active = section.id === `screen-${normalized}`;
    section.classList.toggle("active", active);
  });

  els.navButtons.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.screen === normalized);
  });

  const meta = screenMeta[normalized];
  els.screenTitle.textContent = meta.title;
  els.screenSubtitle.textContent = meta.subtitle;
}

function navigate(screen) {
  window.location.hash = `#${screen}`;
}

function applyRouteFromHash() {
  const raw = window.location.hash.replace("#", "").trim();
  setScreen(normalizeScreen(raw || "dashboard"));
}

function renderAuthGate() {
  if (!state.auth.authenticated) {
    els.appShell.classList.add("hidden");
    els.authGate.classList.remove("hidden");
    return;
  }

  els.authGate.classList.add("hidden");
  els.appShell.classList.remove("hidden");
}

function applyRoleUI() {
  const isAdmin = state.auth.role === "admin";
  state.allowedScreens = isAdmin ? ["dashboard", "employees", "grants", "exercises"] : ["dashboard", "exercises"];

  document.querySelectorAll(".admin-only").forEach((el) => {
    el.classList.toggle("hidden", !isAdmin);
  });

  els.currentUserName.textContent = state.auth.full_name || state.auth.email;
  els.currentUserMeta.textContent = `${state.auth.role || "employee"} | ${state.auth.email || "-"}`;
  els.workspaceSubtitle.textContent = isAdmin ? "Equity operations workspace" : "Your ESOP workspace";
  els.poolPanel.classList.toggle("hidden", !isAdmin);

  if (!state.allowedScreens.includes(state.currentScreen)) {
    navigate("dashboard");
  }
}

function renderMetrics() {
  const summary = state.dashboard;
  if (!summary) {
    els.metricsGrid.innerHTML = '<article class="panel"><div class="empty">No metrics available yet.</div></article>';
    return;
  }

  const isAdmin = state.auth.role === "admin";
  const metrics = isAdmin
    ? [
        ["Total Employees", summary.total_employees],
        ["Active Employees", summary.active_employees],
        ["Total Grants", summary.total_grants],
        ["Pool Allocated", summary.pool_allocated],
        ["Pool Remaining", summary.pool_remaining],
        ["Vested Options", summary.vested_options],
        ["Unvested Options", summary.unvested_options],
        ["Exercised Options", summary.exercised_options],
      ]
    : [
        ["My Grants", summary.total_grants],
        ["Vested Options", summary.vested_options],
        ["Unvested Options", summary.unvested_options],
        ["Exercised Options", summary.exercised_options],
      ];

  els.metricsGrid.innerHTML = metrics
    .map(
      ([label, value]) =>
        `<article class="panel fade-item"><div class="kpi-title">${escapeHtml(label)}</div><div class="kpi-value">${formatInt(value)}</div></article>`
    )
    .join("");

  const poolPercent = summary.pool_size > 0 ? Math.min((summary.pool_allocated / summary.pool_size) * 100, 100) : 0;
  els.poolProgressBar.style.width = `${poolPercent.toFixed(2)}%`;
  els.poolText.textContent = `${formatInt(summary.pool_allocated)} allocated out of ${formatInt(summary.pool_size)} (${poolPercent.toFixed(1)}%)`;
}

function renderDashboardGrants() {
  const rows = state.dashboard?.grant_summaries || [];
  if (!rows.length) {
    els.dashboardGrantTableBody.innerHTML = '<tr><td class="empty" colspan="6">No grants created yet.</td></tr>';
    return;
  }

  els.dashboardGrantTableBody.innerHTML = rows
    .map(
      (row) =>
        `<tr>
          <td>${escapeHtml(row.grant_name)} (#${row.grant_id})</td>
          <td>${escapeHtml(row.employee_name)}</td>
          <td>${formatInt(row.total_options)}</td>
          <td>${formatInt(row.vested_options)}</td>
          <td>${formatInt(row.exercised_options)}</td>
          <td>${formatInt(row.available_to_exercise)}</td>
        </tr>`
    )
    .join("");
}

function filteredEmployees() {
  const search = state.employeeSearch.trim().toLowerCase();
  return state.employees.filter((employee) => {
    const statusMatches = state.employeeStatus === "all" || employee.status === state.employeeStatus;
    if (!statusMatches) {
      return false;
    }

    if (!search) {
      return true;
    }

    const haystack = `${employee.full_name} ${employee.employee_code} ${employee.email}`.toLowerCase();
    return haystack.includes(search);
  });
}

function renderEmployees() {
  const employees = filteredEmployees();
  if (els.employeeCountText) {
    els.employeeCountText.textContent = `${employees.length} records`;
  }

  if (!employees.length) {
    els.employeesTableBody.innerHTML = '<tr><td class="empty" colspan="6">No matching employees.</td></tr>';
  } else {
    els.employeesTableBody.innerHTML = employees
      .map(
        (employee) =>
          `<tr>
            <td>${employee.id}</td>
            <td>${escapeHtml(employee.employee_code)}</td>
            <td>${escapeHtml(employee.full_name)}</td>
            <td>${escapeHtml(employee.email)}</td>
            <td>${escapeHtml(employee.status)}</td>
            <td>${formatDate(employee.joining_date)}</td>
          </tr>`
      )
      .join("");
  }

  const activeEmployees = state.employees.filter((employee) => employee.status === "active");
  els.grantEmployeeSelect.innerHTML = activeEmployees
    .map(
      (employee) =>
        `<option value="${employee.id}">${escapeHtml(employee.full_name)} (${escapeHtml(employee.employee_code)})</option>`
    )
    .join("");
}

function combinedGrantRows() {
  const search = state.grantSearch.trim().toLowerCase();

  return state.grants
    .map((grant) => {
      const employee = getEmployeeById(grant.employee_id);
      const summary = getSummaryByGrantId(grant.id);

      return {
        ...grant,
        employee_name: employee?.full_name || "Unknown",
        employee_code: employee?.employee_code || "-",
        vested_options: summary?.vested_options ?? 0,
        available_to_exercise: summary?.available_to_exercise ?? 0,
      };
    })
    .filter((row) => {
      if (!search) {
        return true;
      }
      const haystack = `${row.grant_name} ${row.employee_name} ${row.employee_code}`.toLowerCase();
      return haystack.includes(search);
    });
}

function renderGrants() {
  const rows = combinedGrantRows();
  if (els.grantCountText) {
    els.grantCountText.textContent = `${rows.length} grants`;
  }

  if (!rows.length) {
    els.grantsTableBody.innerHTML = '<tr><td class="empty" colspan="7">No grants to display.</td></tr>';
  } else {
    els.grantsTableBody.innerHTML = rows
      .map(
        (grant) =>
          `<tr>
            <td>${escapeHtml(grant.grant_name)} (#${grant.id})</td>
            <td>${escapeHtml(grant.employee_name)}<br /><span class="hint">${escapeHtml(grant.employee_code)}</span></td>
            <td>${formatInt(grant.total_options)}</td>
            <td>${formatMoneyFromCents(grant.strike_price_cents)}</td>
            <td>${grant.cliff_months}m cliff / ${grant.vesting_months}m total</td>
            <td>${formatInt(grant.vested_options)}</td>
            <td>${formatInt(grant.available_to_exercise)}</td>
          </tr>`
      )
      .join("");
  }

  const grantOptions = state.grants
    .map((grant) => {
      const employee = getEmployeeById(grant.employee_id);
      const employeeName = employee?.full_name || "Unknown";
      return `<option value="${grant.id}">${escapeHtml(grant.grant_name)} - ${escapeHtml(employeeName)}</option>`;
    })
    .join("");

  els.exerciseGrantSelect.innerHTML = grantOptions;
  els.exerciseHistoryGrantSelect.innerHTML = grantOptions;

  if (state.selectedExerciseGrantId === null && state.grants.length > 0) {
    state.selectedExerciseGrantId = state.grants[0].id;
  }

  if (state.selectedExerciseGrantId !== null) {
    const idAsString = String(state.selectedExerciseGrantId);
    els.exerciseGrantSelect.value = idAsString;
    els.exerciseHistoryGrantSelect.value = idAsString;
  }
}

async function loadExerciseHistory(grantId) {
  if (!grantId) {
    state.exerciseHistory = [];
    renderExerciseHistory();
    return;
  }

  const data = await api(`/api/grants/${grantId}/exercises`);
  state.exerciseHistory = data;
  renderExerciseHistory();
}

function renderExerciseHistory() {
  const grantId = Number(state.selectedExerciseGrantId || 0);
  const grant = state.grants.find((row) => row.id === grantId) || null;
  const summary = getSummaryByGrantId(grantId);

  if (!grant) {
    els.exerciseGrantSummary.textContent = "No grants available.";
    els.exerciseTableBody.innerHTML = '<tr><td class="empty" colspan="4">No data available.</td></tr>';
    return;
  }

  const employee = getEmployeeById(grant.employee_id);
  const employeeName = employee?.full_name || "Unknown";
  els.exerciseGrantSummary.textContent = `${grant.grant_name} for ${employeeName} | Vested ${formatInt(
    summary?.vested_options || 0
  )} | Available ${formatInt(summary?.available_to_exercise || 0)}`;

  if (!state.exerciseHistory.length) {
    els.exerciseTableBody.innerHTML = '<tr><td class="empty" colspan="4">No exercises recorded for this grant.</td></tr>';
    return;
  }

  els.exerciseTableBody.innerHTML = state.exerciseHistory
    .map((exercise) => {
      const totalCost = Number(exercise.price_per_option_cents || 0) * Number(exercise.options_exercised || 0);
      return `<tr>
        <td>${formatDate(exercise.exercise_date)}</td>
        <td>${formatInt(exercise.options_exercised)}</td>
        <td>${formatMoneyFromCents(exercise.price_per_option_cents)}</td>
        <td>${formatMoneyFromCents(totalCost)}</td>
      </tr>`;
    })
    .join("");
}

async function refreshCoreData() {
  const [employees, grants, dashboard] = await Promise.all([
    fetchAllPaginated("/api/employees"),
    fetchAllPaginated("/api/grants"),
    api(`/api/dashboard/summary?as_of=${state.asOf}`),
  ]);

  state.employees = employees;
  state.grants = grants;
  state.dashboard = dashboard;

  const hasSelectedGrant = state.grants.some((grant) => grant.id === state.selectedExerciseGrantId);
  if (!hasSelectedGrant) {
    state.selectedExerciseGrantId = state.grants.length ? state.grants[0].id : null;
  }

  renderMetrics();
  renderDashboardGrants();
  renderEmployees();
  renderGrants();

  if (state.selectedExerciseGrantId) {
    await loadExerciseHistory(state.selectedExerciseGrantId);
  } else {
    renderExerciseHistory();
  }
}

function setupNav() {
  els.navButtons.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      navigate(btn.dataset.screen);
    });
  });

  window.addEventListener("hashchange", applyRouteFromHash);
  applyRouteFromHash();
}

function setupFilters() {
  if (els.employeeSearch) {
    els.employeeSearch.addEventListener("input", (event) => {
      state.employeeSearch = event.target.value;
      renderEmployees();
    });
  }

  if (els.employeeStatusFilter) {
    els.employeeStatusFilter.addEventListener("change", (event) => {
      state.employeeStatus = event.target.value;
      renderEmployees();
    });
  }

  if (els.grantSearch) {
    els.grantSearch.addEventListener("input", (event) => {
      state.grantSearch = event.target.value;
      renderGrants();
    });
  }
}

function setupTopbar() {
  els.asOfDate.value = state.asOf;
  els.asOfDate.addEventListener("change", async (event) => {
    state.asOf = event.target.value || new Date().toISOString().slice(0, 10);
    els.asOfDate.value = state.asOf;
    await refreshCoreData().catch((error) => {
      showToast(error.message, "error");
    });
  });

  els.refreshDataBtn.addEventListener("click", async () => {
    await refreshCoreData()
      .then(() => showToast("Data refreshed"))
      .catch((error) => showToast(error.message, "error"));
  });

  els.logoutBtn.addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    state.auth.authenticated = false;
    renderAuthGate();
    showToast("Logged out");
  });
}

function setupForms() {
  const today = new Date().toISOString().slice(0, 10);

  if (els.employeeForm) {
    els.employeeForm.querySelector('input[name="joining_date"]').value = today;
  }
  if (els.grantForm) {
    els.grantForm.querySelector('input[name="grant_date"]').value = today;
    els.grantForm.querySelector('input[name="vesting_start_date"]').value = today;
  }
  if (els.exerciseForm) {
    els.exerciseForm.querySelector('input[name="exercise_date"]').value = today;
  }

  if (state.auth.role === "admin" && els.employeeForm) {
    els.employeeForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearMessage(els.employeeMessage);
      const formData = new FormData(event.target);

      const payload = {
        employee_code: String(formData.get("employee_code") || "").trim(),
        full_name: String(formData.get("full_name") || "").trim(),
        email: String(formData.get("email") || "").trim(),
        joining_date: formData.get("joining_date"),
        status: "active",
      };

      try {
        await api("/api/employees", { method: "POST", body: JSON.stringify(payload) });
        setMessage(els.employeeMessage, "Employee created", true);
        event.target.reset();
        els.employeeForm.querySelector('input[name="joining_date"]').value = today;
        await refreshCoreData();
        showToast("Employee added");
      } catch (error) {
        setMessage(els.employeeMessage, error.message, false);
        showToast(error.message, "error");
      }
    });
  }

  if (state.auth.role === "admin" && els.grantForm) {
    els.grantForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearMessage(els.grantMessage);
      const formData = new FormData(event.target);

      const payload = {
        employee_id: Number(formData.get("employee_id")),
        grant_name: String(formData.get("grant_name") || "").trim(),
        grant_date: formData.get("grant_date"),
        vesting_start_date: formData.get("vesting_start_date"),
        total_options: Number(formData.get("total_options")),
        strike_price_cents: dollarsToCents(formData.get("strike_price_dollars")),
        cliff_months: Number(formData.get("cliff_months")),
        vesting_months: Number(formData.get("vesting_months")),
        vesting_frequency_months: Number(formData.get("vesting_frequency_months")),
        notes: String(formData.get("notes") || "").trim() || null,
      };

      try {
        await api("/api/grants", { method: "POST", body: JSON.stringify(payload) });
        setMessage(els.grantMessage, "Grant created", true);
        event.target.reset();
        els.grantForm.querySelector('input[name="grant_date"]').value = today;
        els.grantForm.querySelector('input[name="vesting_start_date"]').value = today;
        els.grantForm.querySelector('input[name="grant_name"]').value = "ESOP Grant";
        els.grantForm.querySelector('input[name="cliff_months"]').value = "12";
        els.grantForm.querySelector('input[name="vesting_months"]').value = "48";
        els.grantForm.querySelector('input[name="vesting_frequency_months"]').value = "1";
        await refreshCoreData();
        showToast("Grant created");
      } catch (error) {
        setMessage(els.grantMessage, error.message, false);
        showToast(error.message, "error");
      }
    });
  }

  els.exerciseHistoryGrantSelect.addEventListener("change", async (event) => {
    const grantId = Number(event.target.value);
    state.selectedExerciseGrantId = grantId;
    if (state.auth.role === "admin") {
      els.exerciseGrantSelect.value = String(grantId);
    }
    await loadExerciseHistory(grantId).catch((error) => showToast(error.message, "error"));
  });

  if (state.auth.role === "admin") {
    els.exerciseGrantSelect.addEventListener("change", async (event) => {
      const grantId = Number(event.target.value);
      state.selectedExerciseGrantId = grantId;
      els.exerciseHistoryGrantSelect.value = String(grantId);
      await loadExerciseHistory(grantId).catch((error) => showToast(error.message, "error"));
    });

    els.exerciseForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearMessage(els.exerciseMessage);
      const formData = new FormData(event.target);
      const grantId = Number(formData.get("grant_id"));

      const payload = {
        exercise_date: formData.get("exercise_date"),
        options_exercised: Number(formData.get("options_exercised")),
        price_per_option_cents: dollarsToCents(formData.get("price_per_option_dollars")),
      };

      try {
        await api(`/api/grants/${grantId}/exercises`, { method: "POST", body: JSON.stringify(payload) });
        setMessage(els.exerciseMessage, "Exercise recorded", true);
        event.target.reset();
        els.exerciseForm.querySelector('input[name="exercise_date"]').value = today;
        state.selectedExerciseGrantId = grantId;
        await refreshCoreData();
        showToast("Exercise recorded");
      } catch (error) {
        setMessage(els.exerciseMessage, error.message, false);
        showToast(error.message, "error");
      }
    });
  }
}

async function loadSession() {
  const session = await api("/api/auth/me");
  if (!session.authenticated || !session.user) {
    state.auth = { authenticated: false, role: null, full_name: "", email: "", employee_id: null };
    return;
  }

  state.auth = {
    authenticated: true,
    role: session.user.role,
    full_name: session.user.full_name,
    email: session.user.email,
    employee_id: session.user.employee_id,
  };
}

async function bootstrap() {
  await loadSession();
  renderAuthGate();

  if (!state.auth.authenticated) {
    return;
  }

  applyRoleUI();
  setupNav();
  setupTopbar();
  setupFilters();
  setupForms();

  await refreshCoreData();
}

bootstrap().catch((error) => {
  showToast(error.message, "error");
});
