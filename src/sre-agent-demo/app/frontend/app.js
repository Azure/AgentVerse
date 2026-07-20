"use strict";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const state = { scenario: null, revealed: 0, timer: null };

async function j(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

// --- boot -------------------------------------------------------------------

async function boot() {
  try {
    const cfg = await j("/api/config");
    const badge = $("mode-badge");
    if (cfg.mode === "live") {
      badge.textContent = "Live (read-only)";
      badge.classList.add("live");
      $("safety-banner").querySelector("strong").textContent = "Live — read-only.";
    } else {
      badge.textContent = "Guided replay — simulated";
    }
    badge.title = cfg.note || "";
  } catch (_) { $("mode-badge").textContent = "Guided replay"; }

  try {
    const { scenarios } = await j("/api/scenarios");
    renderScenarioList(scenarios);
    if (scenarios.length) selectScenario(scenarios[0].id);
  } catch (e) { $("scenario-list").textContent = "Failed to load scenarios."; }

  try {
    const ctx = await j("/api/context");
    renderContext(ctx);
  } catch (_) {}
}

// --- scenario list ----------------------------------------------------------

function renderScenarioList(scenarios) {
  const box = $("scenario-list");
  box.innerHTML = "";
  scenarios.forEach((s) => {
    const b = el("button", "scenario");
    b.dataset.id = s.id;
    b.appendChild(el("div", "s-title", s.title));
    b.appendChild(el("div", "s-sub", s.service));
    const tags = el("div", "tags");
    tags.appendChild(el("span", "tag sev", s.severity));
    (s.waf || []).forEach((w) => tags.appendChild(el("span", "tag", w)));
    b.appendChild(tags);
    b.addEventListener("click", () => selectScenario(s.id));
    box.appendChild(b);
  });
}

async function selectScenario(id) {
  document.querySelectorAll(".scenario").forEach((n) =>
    n.classList.toggle("active", n.dataset.id === id));
  stopPlay();
  const s = await j(`/api/scenarios/${id}`);
  state.scenario = s;
  state.revealed = 0;

  $("inv-title").textContent = s.title;
  $("inv-summary").textContent = s.summary;

  const meta = $("inv-meta");
  meta.innerHTML = "";
  meta.appendChild(el("span", "chip", `Mode: ${s.mode}`));
  meta.appendChild(el("span", "chip", `Signal: ${s.signal.source}`));
  meta.appendChild(el("span", "chip", s.signal.fired_at));

  $("controls-row").hidden = false;
  $("timeline").innerHTML = "";
  updateProgress();
  revealNext(); // show the first (signal) turn immediately
}

// --- timeline ---------------------------------------------------------------

function turnNode(t) {
  const li = el("li", `turn ${t.role}`);
  li.appendChild(el("div", "role", t.role));
  if (t.title) li.appendChild(el("div", "t-title", t.title));
  if (t.text) li.appendChild(el("div", "t-text", t.text));

  if (t.tool) li.appendChild(el("div", "tool-name", `tool · ${t.tool}`));
  if (t.kql) li.appendChild(el("pre", "kql", t.kql));
  if (t.result) li.appendChild(el("div", "result", t.result));

  if (t.role === "approval") {
    const c = el("div", "approval-card");
    const a = el("div", "a-row"); a.innerHTML = `<b>Action:</b> ${escapeHtml(t.action || "")}`;
    const r = el("div", "a-row"); r.innerHTML = `<b>Risk:</b> ${escapeHtml(t.risk || "")}`;
    c.appendChild(a); c.appendChild(r);
    const actions = el("div", "approval-actions");
    const ap = el("button", "btn", "Approve"); ap.disabled = true;
    const rj = el("button", "btn", "Reject"); rj.disabled = true;
    actions.appendChild(ap); actions.appendChild(rj);
    c.appendChild(actions);
    c.appendChild(el("div", "approval-note",
      "Approvals are shown read-only in this demo and are never executed."));
    li.appendChild(c);
  }
  return li;
}

function revealNext() {
  const s = state.scenario;
  if (!s || state.revealed >= s.turns.length) { stopPlay(); return false; }
  $("timeline").appendChild(turnNode(s.turns[state.revealed]));
  state.revealed += 1;
  updateProgress();
  return state.revealed < s.turns.length;
}

function showAll() {
  stopPlay();
  const s = state.scenario;
  if (!s) return;
  const tl = $("timeline");
  while (state.revealed < s.turns.length) {
    tl.appendChild(turnNode(s.turns[state.revealed]));
    state.revealed += 1;
  }
  updateProgress();
}

function resetTimeline() {
  stopPlay();
  state.revealed = 0;
  $("timeline").innerHTML = "";
  updateProgress();
  revealNext();
}

function startPlay() {
  if (state.timer) return;
  $("btn-play").textContent = "Pause ⏸";
  state.timer = setInterval(() => {
    if (!revealNext()) stopPlay();
  }, 1100);
}
function stopPlay() {
  if (state.timer) { clearInterval(state.timer); state.timer = null; }
  $("btn-play").textContent = "Play ▶";
}

function updateProgress() {
  const s = state.scenario;
  $("progress").textContent = s ? `${state.revealed} / ${s.turns.length} steps` : "";
}

// --- context panels ---------------------------------------------------------

function renderContext(ctx) {
  const caps = $("capabilities"); caps.innerHTML = "";
  (ctx.capabilities || []).forEach((c) => {
    const d = el("div", "cap");
    d.appendChild(el("div", "c-title", c.title));
    d.appendChild(el("div", "c-text", c.text));
    if (c.doc) { const a = el("a", null, "Learn more →"); a.href = c.doc; a.target = "_blank"; a.rel = "noopener"; d.appendChild(a); }
    caps.appendChild(d);
  });

  const waf = $("waf"); waf.innerHTML = "";
  (ctx.waf || []).forEach((w) => {
    const d = el("div", "waf-item");
    d.appendChild(el("div", "w-pillar", w.pillar));
    d.appendChild(el("div", "w-text", w.text));
    if (w.doc) { const a = el("a", null, "WAF guidance →"); a.href = w.doc; a.target = "_blank"; a.rel = "noopener"; d.appendChild(a); }
    waf.appendChild(d);
  });

  const docs = $("docs"); docs.innerHTML = "";
  const labels = {
    overview: "SRE Agent overview", how_it_works: "How it works",
    api: "API reference", modes: "Agent modes", approvals: "Approvals",
    security: "Security", billing: "Pricing & billing", waf: "Well-Architected Framework",
  };
  Object.keys(labels).forEach((k) => {
    if (!ctx.docs || !ctx.docs[k]) return;
    const a = el("a", null, labels[k]); a.href = ctx.docs[k]; a.target = "_blank"; a.rel = "noopener";
    docs.appendChild(a);
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// --- wire controls ----------------------------------------------------------

$("btn-step").addEventListener("click", () => { stopPlay(); revealNext(); });
$("btn-play").addEventListener("click", () => { state.timer ? stopPlay() : startPlay(); });
$("btn-all").addEventListener("click", showAll);
$("btn-reset").addEventListener("click", resetTimeline);

boot();
