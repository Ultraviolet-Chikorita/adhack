const state = {
  detail: null,
  report: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function badge(label, kind = "good") {
  return `<span class="badge ${kind}">${label}</span>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function pretty(value) {
  return escapeHtml(JSON.stringify(value, null, 2));
}

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  setTimeout(() => node.remove(), 2800);
}

async function refresh() {
  const [detail, report] = await Promise.all([
    api("/state/detail"),
    api("/policy/report"),
  ]);
  state.detail = detail;
  state.report = report;
  render();
}

function render() {
  const { detail, report } = state;
  if (!detail || !report) return;

  $("#metric-spend").textContent = money(detail.summary.total_spend);
  $("#metric-approvals").textContent = detail.summary.pending_approvals;
  $("#metric-policy").textContent = report.flags.policy_hits;
  const riskScore = report.risk_score ?? report.readiness_score ?? 0;
  $("#metric-risk").textContent = `${riskScore}`;

  $("#overmind-status").textContent = detail.supervision.enabled ? "Enabled" : "Local only";
  $("#overmind-detail").textContent = detail.supervision.error || `${detail.supervision.service_name} / ${detail.supervision.environment}`;
  $("#mcp-status").textContent = "Ready";
  $("#mcp-detail").textContent = `${detail.mcp.tools} tools at ${detail.mcp.endpoint}`;

  renderFlagBoard(report);
  renderContracts(report.contracts);
  renderCreatives(detail.creatives, detail.judgements);
  renderPlacements(detail.placements);
  renderTrace(detail.events);
}

function renderFlagBoard(report) {
  const rows = [
    ["Money", report.flags.money_escalations, "Spend spike or cap/ceiling escalation"],
    ["Creative", report.flags.creative_blocks, "Off-brand, unverifiable, or low-confidence variant"],
    ["Waste", report.flags.auto_paused_placements, "ROAS below floor and placement paused"],
    ["Trace", report.flags.policy_hits, "Executable policy-hit events"],
  ];
  $("#flag-board").innerHTML = rows
    .map(([name, count, description]) => {
      const kind = count > 0 ? "danger" : "good";
      const label = count > 0 ? "flagged" : "clear";
      return `
        <div class="flag">
          ${badge(label, kind)}
          <div>
            <strong>${name}</strong>
            <div>${description}</div>
            <small>${count} events</small>
          </div>
        </div>`;
    })
    .join("");
}

function renderContracts(contracts) {
  $("#contracts").innerHTML = contracts
    .map((contract) => {
      const kind = contract.status === "FLAGGED" ? "danger" : "good";
      return `
        <article class="contract">
          <strong>${escapeHtml(contract.name)}</strong>
          <div><small>Agent can act</small><br />${escapeHtml(contract.agent_can_act)}</div>
          <div><small>Human boundary</small><br />${escapeHtml(contract.human_boundary)}</div>
          ${badge(contract.status, kind)}
        </article>`;
    })
    .join("");
}

function renderCreatives(creatives, judgements) {
  const judgementById = Object.fromEntries(judgements.map((j) => [j.creative_id, j]));
  if (!creatives.length) {
    $("#creative-list").innerHTML = `<div class="creative">No creative variants yet.</div>`;
    return;
  }
  $("#creative-list").innerHTML = creatives
    .map((creative) => {
      const judgement = judgementById[creative.id];
      const verdict = judgement?.verdict || "UNJUDGED";
      const kind = verdict === "PASS" ? "good" : verdict === "UNJUDGED" ? "warn" : "danger";
      return `
        <article class="creative">
          <div>${badge(verdict, kind)} <strong>${escapeHtml(creative.headline)}</strong></div>
          <div>${escapeHtml(creative.body)}</div>
          <small>Claim: ${escapeHtml(creative.claim || "none")}</small>
          ${
            judgement
              ? `<small>Reason: ${escapeHtml(judgement.reason)}</small>
                 <small>Judge: ${escapeHtml((judgement.judge_source || "unknown").toUpperCase())}</small>
                 <small>Source: ${judgement.source_url ? `<a href="${escapeHtml(judgement.source_url)}" target="_blank">verified source</a>` : "none"}</small>`
              : ""
          }
          <div class="creative-actions">
            <button data-judge="${creative.id}">Judge</button>
          </div>
        </article>`;
    })
    .join("");
  $$("[data-judge]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/creative/judge/${button.dataset.judge}`, { method: "POST" });
      toast("Creative judged.");
      await refresh();
    });
  });
}

function renderPlacements(placements) {
  if (!placements.length) {
    $("#placements-table").innerHTML = `<div class="placement-row">No placements yet.</div>`;
    return;
  }
  $("#placements-table").innerHTML = placements
    .map((p) => {
      const roas = p.spend > 0 ? p.revenue / p.spend : 0;
      return `
        <div class="placement-row">
          <strong>${escapeHtml(p.placement_id)}</strong>
          <span>${p.impressions} imps</span>
          <span>${p.clicks} clicks</span>
          <span>${money(p.spend)}</span>
          <span>ROAS ${roas.toFixed(2)}</span>
          ${badge(p.paused ? "paused" : "active", p.paused ? "danger" : "good")}
        </div>`;
    })
    .join("");
}

function renderTrace(events) {
  $("#trace-list").innerHTML = events
    .slice(0, 40)
    .map((event) => `
      <article class="event">
        <div class="event-title">
          <strong>${escapeHtml(event.event_type)}</strong>
          <small>${escapeHtml(event.created_at)}</small>
        </div>
        <div>${escapeHtml(event.message)}</div>
        <pre class="event-payload">${pretty(event.payload)}</pre>
      </article>`)
    .join("");
}

function wireTabs() {
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => t.classList.remove("active"));
      $$(".panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      $(`#panel-${tab.dataset.tab}`).classList.add("active");
    });
  });
}

function wireActions() {
  $("#run-demo").addEventListener("click", async () => {
    await api("/demo/run", { method: "POST" });
    toast("Seeded guardrail demo complete.");
    await refresh();
  });

  $("#refresh").addEventListener("click", refresh);

  $("#evaluate-bid").addEventListener("click", async () => {
    const body = {
      prompt: $("#prompt-input").value,
      placement_id: $("#placement-input").value,
    };
    const result = await api("/bid/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    });
    $("#bid-output").innerHTML = pretty(result);
    await refresh();
  });

  $("#generate-creatives").addEventListener("click", async () => {
    await api("/creative/generate", {
      method: "POST",
      body: JSON.stringify({
        prompt: $("#creative-prompt").value,
        placement_id: $("#placement-input").value,
      }),
    });
    toast("Creative variants generated.");
    await refresh();
  });

  $("#evaluate-waste").addEventListener("click", async () => {
    const placementId = $("#waste-placement").value;
    const payload = {
      placement_id: placementId,
      impressions: Number($("#waste-impressions").value),
      clicks: Number($("#waste-clicks").value),
      spend: Number($("#waste-spend").value),
      revenue: Number($("#waste-revenue").value),
      paused: false,
      pause_reason: null,
    };
    await api("/placements/upsert", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const result = await api(`/placements/evaluate-waste/${encodeURIComponent(placementId)}`, {
      method: "POST",
    });
    $("#waste-output").innerHTML = pretty(result);
    await refresh();
  });
}

wireTabs();
wireActions();
refresh().catch((error) => {
  console.error(error);
  toast(`Unable to load console: ${error.message}`);
});

setInterval(() => {
  refresh().catch((error) => console.error(error));
}, 8000);
