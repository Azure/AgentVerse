/* Planner dashboard: renders the schedule board and streams pipeline events.
   Same-origin API (the backend serves this page), so no base URL config. */

const $ = (id) => document.getElementById(id);
const HORIZON = 15; // hours shown on the board

let lastState = null;
let movedOrders = new Set();
let running = false;

// ---- rendering -----------------------------------------------------------------

function renderState(state) {
  lastState = state;
  $("mode-badge").textContent = state.mode === "replay" ? "replay mode · no Azure" : "live · Foundry Agents";
  $("mode-badge").className = "badge " + state.mode;

  $("kpi-version").textContent = "v" + state.kpis.schedule_version;
  $("kpi-idle").textContent = state.kpis.idle_hours + " h";
  $("kpi-adherence").textContent = state.kpis.adherence_pct + " %";
  $("kpi-auto").textContent = state.counters.auto_applied + " / " + state.counters.escalations;
  $("kpi-adjust").textContent =
    state.counters.last_adjust_seconds == null ? "–" : state.counters.last_adjust_seconds + " s";
  $("gantt-version").textContent = "· v" + state.schedule.version;

  renderGantt(state);
}

function renderGantt(state) {
  const gantt = $("gantt");
  gantt.innerHTML = "";

  const axis = document.createElement("div");
  axis.className = "gantt-row axis";
  axis.innerHTML = "<div class='gantt-label'></div><div class='gantt-track'>" +
    Array.from({ length: HORIZON + 1 }, (_, h) =>
      `<span class="tick" style="left:${(h / HORIZON) * 100}%">${h}h</span>`).join("") +
    "</div>";
  gantt.appendChild(axis);

  for (const machine of state.machines) {
    const row = document.createElement("div");
    row.className = "gantt-row";
    const down = machine.status === "down" || machine.status === "maintenance";
    row.innerHTML =
      `<div class="gantt-label">${machine.id}` +
      (down ? ` <span class="down-badge">${machine.status}</span>` : "") +
      `</div>`;

    const track = document.createElement("div");
    track.className = "gantt-track" + (down ? " down" : "");
    if (down && machine.available_from_hour > 0) {
      const repair = document.createElement("div");
      repair.className = "repair-window";
      repair.style.width = (machine.available_from_hour / HORIZON) * 100 + "%";
      repair.title = `down until +${machine.available_from_hour}h`;
      track.appendChild(repair);
    }

    for (const slot of state.schedule.slots.filter((s) => s.machine_id === machine.id)) {
      const order = state.orders[slot.order_id] || {};
      const block = document.createElement("div");
      const tier1 = order.customer_tier === "tier1";
      block.className = "slot" + (tier1 ? " tier1" : "") + (movedOrders.has(slot.order_id) ? " moved" : "");
      block.style.left = (slot.start_hour / HORIZON) * 100 + "%";
      block.style.width = (Math.min(slot.end_hour, HORIZON) - slot.start_hour) / HORIZON * 100 + "%";
      block.title = `${slot.order_id} (${order.product || "?"}) +${slot.start_hour}h → +${slot.end_hour}h` +
        (order.due_hours != null ? ` · due +${order.due_hours}h` : "");
      block.textContent = slot.order_id.replace("ORD-", "");
      track.appendChild(block);
    }
    row.appendChild(track);
    gantt.appendChild(row);
  }
}

function feedLine(html, cls = "") {
  const feed = $("feed");
  if (feed.querySelector(".muted")) feed.innerHTML = "";
  const p = document.createElement("div");
  p.className = "feed-line " + cls;
  p.innerHTML = html;
  feed.appendChild(p);
  feed.scrollTop = feed.scrollHeight;
}

const AGENT_ICON = {
  "constraint-monitor": "📡", "scenario-simulator": "🧪",
  "schedule-orchestrator": "🎯", "schedule-dispatcher": "📤",
};

// ---- pipeline stream --------------------------------------------------------------

function runDisruption(key) {
  if (running) return;
  running = true;
  movedOrders = new Set();
  $("escalation").classList.add("hidden");
  $("decision").classList.add("hidden");
  feedLine(`<b>— injecting <code>${key}</code> —</b>`, "divider");
  document.querySelectorAll(".disrupt").forEach((b) => (b.disabled = true));

  const source = new EventSource(`/api/run/${key}`);
  source.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    handleEvent(ev);
    if (ev.type === "done" || ev.type === "error") {
      source.close();
      running = false;
      document.querySelectorAll(".disrupt").forEach((b) => (b.disabled = false));
    }
  };
  source.onerror = () => {
    source.close();
    running = false;
    document.querySelectorAll(".disrupt").forEach((b) => (b.disabled = false));
  };
}

function handleEvent(ev) {
  switch (ev.type) {
    case "agent_start":
      feedLine(`${AGENT_ICON[ev.agent] || "🤖"} <b>${ev.agent}</b> working…`);
      break;
    case "agent_log":
      feedLine(`&nbsp;&nbsp;· ${ev.message}`, "log");
      break;
    case "agent_done":
      if (ev.agent === "schedule-orchestrator") {
        const p = ev.payload;
        feedLine(`🎯 decision: <b>${p.decision}</b> (confidence ${p.confidence.toFixed(2)})`);
      } else if (ev.agent === "schedule-dispatcher") {
        (ev.payload.notifications || []).forEach((n) => feedLine(`&nbsp;&nbsp;→ ${n}`, "log"));
        feedLine(`📤 published <b>v${ev.payload.schedule_version}</b>`);
      } else if (ev.agent === "constraint-monitor") {
        const p = ev.payload;
        feedLine(`&nbsp;&nbsp;· classified <b>${p.type}</b> (severity ${p.severity})` +
          (p.security_flag ? ` <span class="flag">security flag</span>` : ""), "log");
      } else {
        feedLine(`&nbsp;&nbsp;· ${ev.agent} done`, "log");
      }
      break;
    case "escalation":
      showEscalation(ev);
      break;
    case "decision":
      showDecision(ev.payload);
      break;
    case "schedule_updated":
      movedOrders = new Set(); // recompute below via diff
      diffMoved(ev.schedule);
      break;
    case "state":
      renderState(ev.payload);
      break;
    case "error":
      feedLine(`❌ ${ev.message}`, "flag");
      break;
  }
}

function diffMoved(newSchedule) {
  if (!lastState) return;
  const before = {};
  for (const s of lastState.schedule.slots) before[s.order_id] = `${s.machine_id}|${s.start_hour}`;
  for (const s of newSchedule.slots) {
    if (before[s.order_id] && before[s.order_id] !== `${s.machine_id}|${s.start_hour}`) movedOrders.add(s.order_id);
    if (!before[s.order_id]) movedOrders.add(s.order_id);
  }
}

function showDecision(p) {
  const card = $("decision");
  card.className = "card " + (p.security_flag ? "rejected" : p.decision === "auto_reschedule" ? "auto" : "");
  $("decision-title").textContent =
    p.security_flag ? "🛑 Rejected — manipulation attempt detected"
      : p.decision === "auto_reschedule" ? "✅ Rescheduled autonomously"
      : p.decision === "escalate_to_planner" ? "👤 Escalated to you"
      : "🛑 Rejected";
  $("decision-rationale").textContent = p.rationale;
}

function showEscalation(ev) {
  $("escalation-rationale").textContent = ev.rationale;
  const box = $("escalation-options");
  box.innerHTML = "";
  for (const option of ev.options) {
    const id = option.split(":")[0].trim();
    const btn = document.createElement("button");
    btn.className = "option";
    btn.innerHTML = `<b>${id}</b><span>${option.slice(id.length + 1).trim()}</span>`;
    btn.onclick = () => chooseScenario(id, option);
    box.appendChild(btn);
  }
  $("escalation").classList.remove("hidden");
}

async function chooseScenario(id, label) {
  const res = await fetch("/api/choose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: id }),
  });
  if (!res.ok) { feedLine(`❌ choose failed: ${(await res.json()).detail}`, "flag"); return; }
  const data = await res.json();
  $("escalation").classList.add("hidden");
  feedLine(`👤 planner chose <b>${id}</b>`);
  data.notifications.forEach((n) => feedLine(`&nbsp;&nbsp;→ ${n}`, "log"));
  feedLine(`📤 published <b>v${data.schedule_version}</b>`);
  diffMoved(data.state.schedule);
  renderState(data.state);
}

// ---- wiring -------------------------------------------------------------------------

document.querySelectorAll(".disrupt").forEach((btn) =>
  btn.addEventListener("click", () => runDisruption(btn.dataset.key)));

$("reset-btn").addEventListener("click", async () => {
  const state = await (await fetch("/api/reset", { method: "POST" })).json();
  movedOrders = new Set();
  $("feed").innerHTML = "<p class='muted'>Plant reset. Inject a disruption to watch the agents work.</p>";
  $("escalation").classList.add("hidden");
  $("decision").classList.add("hidden");
  renderState(state);
});

fetch("/api/state").then((r) => r.json()).then(renderState);
