/* Model Evaluator — vanilla JS front end.
 * - Auto-discovers deployments from /api/models (newly deployed models appear on Refresh).
 * - Sends ONE shared prompt to both models in parallel via /api/compare (SSE over fetch).
 * - Renders latency / TTFT / tokens / throughput per model; all model text is inserted
 *   with textContent (never innerHTML) since it is untrusted.
 * - Optional explicit blind judge, JSON/CSV export, browser-local history.
 */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const HISTORY_KEY = "model-evaluator-history-v1";

  const el = {
    a: $("model-a"), b: $("model-b"), metaA: $("meta-a"), metaB: $("meta-b"),
    refresh: $("refresh"), source: $("source-badge"),
    system: $("system"), temperature: $("temperature"), top_p: $("top_p"),
    max_tokens: $("max_tokens"), seed: $("seed"), paramHint: $("param-hint"),
    prompt: $("prompt"), run: $("run"), judge: $("judge"),
    exportJson: $("export-json"), exportCsv: $("export-csv"), status: $("status"),
    nameA: $("name-a"), nameB: $("name-b"), verA: $("ver-a"), verB: $("ver-b"),
    metricsA: $("metrics-a"), metricsB: $("metrics-b"),
    answerA: $("answer-a"), answerB: $("answer-b"),
    filterA: $("filter-a"), filterB: $("filter-b"),
    verdict: $("verdict"), verdictBody: $("verdict-body"),
    history: $("history-list"), clearHistory: $("clear-history"),
  };

  let MODELS = [];
  let LIMITS = { max_output_tokens: 1024, max_prompt_chars: 16000, max_models_per_run: 2 };
  let inferenceEnabled = true;
  let lastRun = null; // { prompt, system, params, results: [a, b] }

  // --- helpers --------------------------------------------------------------
  const byName = (n) => MODELS.find((m) => m.name === n) || null;
  const fmtMs = (v) => (v == null ? "—" : `${Math.round(v)} ms`);
  const fmtTok = (v) => (v == null ? "—" : `${v}`);

  function setStatus(msg, kind) {
    el.status.textContent = msg || "";
    el.status.className = "status" + (kind ? " " + kind : "");
  }

  // --- discovery ------------------------------------------------------------
  async function loadModels(refresh) {
    setStatus(refresh ? "Refreshing deployments…" : "Discovering deployments…");
    try {
      const r = await fetch("/api/models" + (refresh ? "?refresh=1" : ""));
      const data = await r.json();
      MODELS = data.models || [];
      LIMITS = data.limits || LIMITS;
      inferenceEnabled = data.inference_enabled !== false;
      renderSource(data);
      populate(el.a, "A");
      populate(el.b, "B");
      restoreSelection();
      onModelChange();
      const sel = data.selectable_count || 0;
      setStatus(sel < 2 ? `Only ${sel} chat-capable model(s) found` : "", sel < 2 ? "warn" : "");
      if (data.error) console.warn("discovery note:", data.error);
    } catch (e) {
      setStatus("Failed to load models: " + e.message, "err");
    }
  }

  function renderSource(data) {
    const map = { project: "Foundry project", arm: "ARM inventory", static: "static list", none: "none", error: "error" };
    const label = map[data.source] || data.source || "—";
    el.source.textContent = "source: " + label;
    el.source.className = "src" + (data.source === "static" || data.source === "none" ? " stale" : "");
  }

  function populate(select, slot) {
    const prev = select.value;
    select.textContent = "";
    for (const m of MODELS) {
      const o = document.createElement("option");
      o.value = m.name;
      const tag = m.selectable ? "" : "  (unsupported: " + m.reason + ")";
      o.textContent = m.name + (m.version ? ` · v${m.version}` : "") + tag;
      o.disabled = !m.selectable;
      if (m.reasoning) o.dataset.reasoning = "1";
      select.appendChild(o);
    }
    if (prev && byName(prev)) select.value = prev;
  }

  function restoreSelection() {
    const selectable = MODELS.filter((m) => m.selectable);
    if (selectable.length >= 2) {
      if (!byName(el.a.value) || !modelSelectable(el.a.value)) el.a.value = selectable[0].name;
      if (!byName(el.b.value) || !modelSelectable(el.b.value) || el.b.value === el.a.value)
        el.b.value = (selectable.find((m) => m.name !== el.a.value) || selectable[1]).name;
    }
  }
  const modelSelectable = (n) => { const m = byName(n); return m && m.selectable; };

  function onModelChange() {
    const ma = byName(el.a.value), mb = byName(el.b.value);
    el.metaA.textContent = metaLine(ma);
    el.metaB.textContent = metaLine(mb);
    const sameChosen = ma && mb && ma.name === mb.name;
    const reasoning = (ma && ma.reasoning) || (mb && mb.reasoning);
    // Reasoning models reject temperature / top_p — disable and explain.
    el.temperature.disabled = !!reasoning;
    el.top_p.disabled = !!reasoning;
    el.paramHint.textContent = reasoning
      ? "A reasoning model is selected → temperature / top-p are ignored for it and disabled."
      : "";
    const ready = inferenceEnabled && ma && mb && ma.selectable && mb.selectable && !sameChosen;
    el.run.disabled = !ready;
    setStatus(sameChosen ? "Pick two different deployments" : "", sameChosen ? "warn" : "");
  }

  function metaLine(m) {
    if (!m) return "";
    const bits = [m.model];
    if (m.version) bits.push("v" + m.version);
    if (m.reasoning) bits.push("reasoning");
    bits.push(m.source);
    return bits.filter(Boolean).join(" · ");
  }

  // --- compare (SSE over fetch) --------------------------------------------
  async function runCompare() {
    if (el.run.disabled) return;
    const prompt = el.prompt.value.trim();
    if (!prompt) { setStatus("Enter a prompt", "warn"); return; }
    if (prompt.length > LIMITS.max_prompt_chars) { setStatus("Prompt too long", "warn"); return; }

    const models = [el.a.value, el.b.value];
    resetResults(models);
    setBusy(true);
    setStatus("Running both models in parallel…");

    const body = {
      prompt, models,
      system: el.system.value.trim(),
      temperature: el.temperature.disabled ? null : numOrNull(el.temperature.value),
      top_p: el.top_p.disabled ? null : numOrNull(el.top_p.value),
      max_tokens: numOrNull(el.max_tokens.value),
      seed: numOrNull(el.seed.value),
    };

    const results = {};
    try {
      const resp = await fetch("/api/compare", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${resp.status}`);
      }
      await readSSE(resp, (event, data) => {
        if (event === "result") {
          results[data.name] = data;
          renderResult(data, models.indexOf(data.name) === 0 ? "A" : "B");
        } else if (event === "error") {
          setStatus(data.message || "error", "err");
        }
      });
      lastRun = { prompt, system: body.system, params: body, results: models.map((n) => results[n]).filter(Boolean) };
      finishRun(models, results);
    } catch (e) {
      setStatus("Compare failed: " + e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function readSSE(resp, onEvent) {
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const raw = buf.slice(0, idx); buf = buf.slice(idx + 2);
        let ev = "message", dataLine = "";
        for (const line of raw.split("\n")) {
          if (line.startsWith("event:")) ev = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLine += line.slice(5).trim();
        }
        if (dataLine) { try { onEvent(ev, JSON.parse(dataLine)); } catch (_) {} }
      }
    }
  }

  function finishRun(models, results) {
    const a = results[models[0]], b = results[models[1]];
    const ok = a && b && !a.error && !b.error;
    el.judge.disabled = !ok;
    el.exportJson.disabled = el.exportCsv.disabled = !(a || b);
    setStatus(ok ? "Done" : "Completed with errors", ok ? "ok" : "warn");
    if (a || b) saveHistory({ prompt: el.prompt.value.trim(), a, b, ts: Date.now() });
  }

  // --- render results -------------------------------------------------------
  function resetResults(models) {
    setSlot("A", models[0]);
    setSlot("B", models[1]);
    el.judge.disabled = true;
    el.verdict.classList.add("hidden");
  }
  function setSlot(slot, name) {
    const m = byName(name);
    el["name" + slot].textContent = name;
    el["ver" + slot].textContent = m && m.version ? "v" + m.version : "";
    el["metrics" + slot].textContent = "";
    el["answer" + slot].textContent = "…";
    el["filter" + slot].textContent = "";
    el["card" + slot] && el["card" + slot].classList.remove("err");
  }

  function renderResult(r, slot) {
    const ans = el["answer" + slot];
    ans.textContent = r.error ? "⚠ " + r.error : (r.text || "(empty response)");
    const card = document.getElementById("card-" + slot.toLowerCase());
    if (card) card.classList.toggle("err", !!r.error);

    const m = el["metrics" + slot];
    m.textContent = "";
    const t = r.tokens || {};
    const chips = [
      ["latency", fmtMs(r.latency_ms)],
      ["TTFT", fmtMs(r.ttft_ms)],
      ["tok/s", r.tokens_per_sec == null ? "—" : r.tokens_per_sec],
      ["prompt tok", fmtTok(t.prompt)],
      ["output tok", fmtTok(t.completion)],
      ["total tok", fmtTok(t.total)],
      ["finish", r.finish_reason || "—"],
    ];
    for (const [k, v] of chips) {
      const c = document.createElement("span");
      c.className = "chip";
      const label = document.createElement("b"); label.textContent = v + " ";
      const sub = document.createElement("small"); sub.textContent = k;
      c.append(label, sub);
      m.appendChild(c);
    }
    const cf = el["filter" + slot];
    cf.textContent = "";
    if (r.content_filter && Object.keys(r.content_filter).length) {
      cf.textContent = "content filter: " + Object.entries(r.content_filter).map(([k, v]) => `${k}=${v}`).join(", ");
    }
  }

  // --- judge ----------------------------------------------------------------
  async function runJudge() {
    if (!lastRun || lastRun.results.length < 2) return;
    const [a, b] = lastRun.results;
    el.judge.disabled = true;
    setStatus("Judging (blind, randomized A/B)…");
    try {
      const resp = await fetch("/api/judge", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: lastRun.prompt,
          a: { name: a.name, text: a.text },
          b: { name: b.name, text: b.text },
        }),
      });
      const data = await resp.json();
      if (!resp.ok || data.error) throw new Error(data.error || `HTTP ${resp.status}`);
      renderVerdict(data);
      setStatus("Judged by " + data.judge_model, "ok");
    } catch (e) {
      setStatus("Judge failed: " + e.message, "err");
    } finally {
      el.judge.disabled = false;
    }
  }

  function renderVerdict(v) {
    el.verdict.classList.remove("hidden");
    const body = el.verdictBody;
    body.textContent = "";

    const head = document.createElement("p");
    head.className = "winner";
    head.textContent = v.winner === "tie" ? "Result: tie" : "Winner: " + v.winner;
    body.appendChild(head);

    const meta = document.createElement("p");
    meta.className = "muted judge-meta";
    let mtext = "Judge: " + (v.judge_model || "?") + (v.judge_version ? " (v" + v.judge_version + ")" : "");
    if (v.selection_reason) mtext += " · " + v.selection_reason;
    meta.textContent = mtext;
    body.appendChild(meta);

    if (v.family_overlap && v.family_overlap.length) {
      const warn = document.createElement("p");
      warn.className = "judge-warn";
      warn.textContent = "⚠ Judge shares a model family with: " + v.family_overlap.join(", ") +
        " — possible self/family preference bias.";
      body.appendChild(warn);
    }

    const criteria = v.criteria || ["helpfulness", "correctness", "completeness", "coherence"];
    const table = document.createElement("table");
    table.className = "scores";
    const names = Object.keys(v.scores || {});
    const thead = document.createElement("tr");
    thead.appendChild(cell("th", "criterion"));
    for (const n of names) thead.appendChild(cell("th", n));
    table.appendChild(thead);
    for (const crit of criteria) {
      const tr = document.createElement("tr");
      tr.appendChild(cell("td", crit));
      for (const n of names) {
        const s = (v.scores[n] || {})[crit];
        tr.appendChild(cell("td", s == null ? "—" : String(s)));
      }
      table.appendChild(tr);
    }
    body.appendChild(table);

    if (v.rationale) { const p = document.createElement("p"); p.className = "rationale"; p.textContent = v.rationale; body.appendChild(p); }
    if (v.note) { const n = document.createElement("p"); n.className = "muted note"; n.textContent = v.note; body.appendChild(n); }
  }
  const cell = (tag, text) => { const c = document.createElement(tag); c.textContent = text; return c; };

  // --- export ---------------------------------------------------------------
  function exportJson() {
    if (!lastRun) return;
    download("model-comparison.json", "application/json",
      JSON.stringify({ prompt: lastRun.prompt, system: lastRun.system, results: lastRun.results }, null, 2));
  }
  function exportCsv() {
    if (!lastRun) return;
    const cols = ["name", "model", "version", "latency_ms", "ttft_ms", "tokens_per_sec",
      "prompt_tokens", "completion_tokens", "total_tokens", "finish_reason", "error"];
    const rows = [cols.join(",")];
    for (const r of lastRun.results) {
      const t = r.tokens || {};
      const vals = [r.name, r.model, r.version, r.latency_ms, r.ttft_ms, r.tokens_per_sec,
        t.prompt, t.completion, t.total, r.finish_reason, r.error];
      rows.push(vals.map(csv).join(","));
    }
    download("model-comparison.csv", "text/csv", rows.join("\n"));
  }
  const csv = (v) => { if (v == null) return ""; const s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  function download(name, type, text) {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // --- history (browser-local) ---------------------------------------------
  function saveHistory(entry) {
    const list = getHistory();
    list.unshift({
      ts: entry.ts, prompt: entry.prompt.slice(0, 200),
      a: slim(entry.a), b: slim(entry.b),
    });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 25)));
    renderHistory();
  }
  const slim = (r) => r ? {
    name: r.name, version: r.version, latency_ms: r.latency_ms, ttft_ms: r.ttft_ms,
    completion: (r.tokens || {}).completion, tokens_per_sec: r.tokens_per_sec, error: r.error || null,
  } : null;
  function getHistory() { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; } }
  function renderHistory() {
    const list = getHistory();
    el.history.textContent = "";
    if (!list.length) { el.history.textContent = "No runs yet."; return; }
    for (const h of list) {
      const row = document.createElement("div"); row.className = "hrow";
      const when = document.createElement("span"); when.className = "hwhen"; when.textContent = new Date(h.ts).toLocaleString();
      const p = document.createElement("span"); p.className = "hprompt"; p.textContent = h.prompt;
      const m = document.createElement("span"); m.className = "hmetrics";
      m.textContent = `${h.a ? h.a.name : "?"} (${fmtMs(h.a && h.a.latency_ms)}) vs ${h.b ? h.b.name : "?"} (${fmtMs(h.b && h.b.latency_ms)})`;
      row.append(when, p, m);
      el.history.appendChild(row);
    }
  }

  // --- misc -----------------------------------------------------------------
  function setBusy(busy) {
    el.run.disabled = busy || el.run.disabled;
    el.run.textContent = busy ? "Running…" : "Compare ▶";
    if (!busy) onModelChange();
  }
  const numOrNull = (v) => { v = (v || "").toString().trim(); if (v === "") return null; const n = Number(v); return Number.isFinite(n) ? n : null; };

  // --- wire up --------------------------------------------------------------
  el.a.addEventListener("change", onModelChange);
  el.b.addEventListener("change", onModelChange);
  el.refresh.addEventListener("click", () => loadModels(true));
  el.run.addEventListener("click", runCompare);
  el.judge.addEventListener("click", runJudge);
  el.exportJson.addEventListener("click", exportJson);
  el.exportCsv.addEventListener("click", exportCsv);
  el.clearHistory.addEventListener("click", () => { localStorage.removeItem(HISTORY_KEY); renderHistory(); });
  el.prompt.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runCompare(); });

  renderHistory();
  loadModels(false);
})();
