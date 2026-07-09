const SVG_NS = "http://www.w3.org/2000/svg";
const CH = [
    { key: "vibration_mm_s", color: "#f97316" },
    { key: "temperature_c", color: "#ef4444" },
    { key: "current_a", color: "#3b82f6" },
];

class SignalToService {
    constructor() {
        this.assets = [];
        this.currentAsset = null;
        this.runId = null;
        this.es = null;
        this.streamGen = 0;          // increments per run so stale callbacks are ignored
        this.streamTerminal = false; // true once a terminal event was received
        this.assetSelect = document.getElementById("assetSelect");
        this.toast = document.getElementById("toast");
        this.bindControls();
        this.init();
    }

    bindControls() {
        document.getElementById("injectBtn").addEventListener("click", () => this.runDiagnose("degrading"));
        document.getElementById("healthyBtn").addEventListener("click", () => this.showHealthy());
        document.getElementById("approveBtn").addEventListener("click", () => this.decide("approve"));
        document.getElementById("rejectBtn").addEventListener("click", () => this.decide("reject"));
        this.assetSelect.addEventListener("change", () => {
            this.currentAsset = this.assetSelect.value;
            this.showHealthy();
        });
    }

    async init() {
        try {
            this.assets = await (await fetch("/api/assets")).json();
            this.assetSelect.innerHTML = this.assets
                .map((a) => `<option value="${a.id}">${a.id} · ${a.model}</option>`)
                .join("");
            this.currentAsset = this.assets[0].id;
            this.showHealthy();
        } catch (e) {
            this.showToast("Could not load assets.");
        }
    }

    assetById(id) { return this.assets.find((a) => a.id === id); }

    async showHealthy() {
        this.resetAll();
        const a = this.assetById(this.currentAsset);
        document.getElementById("assetMeta").innerHTML =
            `<b>${a.id}</b> — ${a.model} · ${a.location} · criticality ` +
            `<span class="badge badge-${a.criticality}">${a.criticality}</span>`;
        const series = await (await fetch(`/api/telemetry?asset=${a.id}&series=healthy`)).json();
        this.drawChart(series);
        document.getElementById("streamStatus").className = "stream-status";
        document.getElementById("streamStatus").textContent =
            "Stream nominal — all channels within thresholds.";
    }

    // ---------------------------------------------------------------- chart
    drawChart(series) {
        const svg = document.getElementById("chart");
        svg.innerHTML = "";
        const W = 760, H = 260, padL = 10, padR = 10, top = 12, bottom = 22;
        const pts = series.points, n = pts.length;
        const x = (i) => padL + (i / (n - 1)) * (W - padL - padR);
        const norm = (v, ch) => Math.min(1, v / (series.alarm[ch] * 1.3));
        const y = (v, ch) => (H - bottom) - norm(v, ch) * (H - bottom - top);

        // alarm reference band (normalised alarm sits at the same height for all channels)
        const alarmY = (H - bottom) - (1 / 1.3) * (H - bottom - top);
        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("x1", padL); line.setAttribute("x2", W - padR);
        line.setAttribute("y1", alarmY); line.setAttribute("y2", alarmY);
        line.setAttribute("stroke", "#fca5a5"); line.setAttribute("stroke-dasharray", "4 4");
        svg.appendChild(line);
        const alabel = document.createElementNS(SVG_NS, "text");
        alabel.setAttribute("x", W - padR - 4); alabel.setAttribute("y", alarmY - 4);
        alabel.setAttribute("text-anchor", "end"); alabel.setAttribute("font-size", "10");
        alabel.setAttribute("fill", "#ef4444"); alabel.textContent = "alarm";
        svg.appendChild(alabel);

        // anomaly shading
        const anom = series.anomaly;
        if (anom && anom.detected && anom.from_index != null) {
            const rect = document.createElementNS(SVG_NS, "rect");
            rect.setAttribute("x", x(anom.from_index)); rect.setAttribute("y", top);
            rect.setAttribute("width", W - padR - x(anom.from_index));
            rect.setAttribute("height", H - bottom - top);
            rect.setAttribute("fill", "#ef4444"); rect.setAttribute("opacity", "0.07");
            svg.appendChild(rect);
        }

        for (const ch of CH) {
            const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p[ch.key], ch.key).toFixed(1)}`).join(" ");
            const path = document.createElementNS(SVG_NS, "path");
            path.setAttribute("d", d); path.setAttribute("fill", "none");
            path.setAttribute("stroke", ch.color); path.setAttribute("stroke-width", "2");
            svg.appendChild(path);
        }
    }

    // ----------------------------------------------------------- diagnose
    runDiagnose(mode) {
        this.resetAll();
        const a = this.assetById(this.currentAsset);
        const gen = ++this.streamGen; // this run's generation token
        this.streamTerminal = false;
        fetch(`/api/telemetry?asset=${a.id}&series=${mode}`)
            .then((r) => r.json())
            .then((s) => {
                if (gen !== this.streamGen) return;
                this.drawChart(s);
                const st = document.getElementById("streamStatus");
                st.className = "stream-status alarm";
                st.textContent = "⚠ Anomaly detected — telemetry breached thresholds. Agent pipeline triggered.";
            });
        document.getElementById("injectBtn").disabled = true;
        this.es = new EventSource(`/api/diagnose?asset=${a.id}&series=${mode}`);
        this.wireCommon(this.es, gen);
        this.es.addEventListener("anomaly_detected", (e) => {
            if (gen !== this.streamGen) return;
            this.runId = JSON.parse(e.data).run_id;
        });
        this.es.addEventListener("diagnosis", (e) => {
            if (gen !== this.streamGen) return;
            this.renderDiagnosis(JSON.parse(e.data).data);
        });
        this.es.addEventListener("knowledge", (e) => {
            if (gen !== this.streamGen) return;
            this.renderSop(JSON.parse(e.data));
        });
        this.es.addEventListener("awaiting_approval", (e) => {
            if (gen !== this.streamGen) return;
            this.showApproval(JSON.parse(e.data));
            // Terminal event for Phase A: close the stream so the browser does
            // NOT auto-reconnect and re-run the whole orchestration.
            this.streamTerminal = true;
            this.closeStream();
        });
    }

    // Wire the events shared by both SSE phases (diagnose + dispatch) and make
    // every failure terminal so a single click triggers exactly one run.
    wireCommon(es, gen) {
        es.addEventListener("agent_start", (e) => { if (gen === this.streamGen) this.agent(JSON.parse(e.data), "running"); });
        es.addEventListener("agent_log", (e) => { if (gen === this.streamGen) this.log(JSON.parse(e.data)); });
        es.addEventListener("agent_done", (e) => { if (gen === this.streamGen) this.agent(JSON.parse(e.data), "done"); });
        es.addEventListener("error", (e) => {
            if (gen !== this.streamGen) return;
            if (e.data) {
                // Application-level error emitted by the server → terminal.
                try { this.showToast(JSON.parse(e.data).message || "Agent error."); } catch { this.showToast("Agent error."); }
                this.streamTerminal = true;
                this.closeStream();
                this.recover();
                return;
            }
            // Transport-level error / connection closed. If we already reached a
            // terminal event this is the normal post-completion close — just
            // release the handle. Otherwise the connection dropped mid-run:
            // close it to stop EventSource from auto-reconnecting (which would
            // start a brand-new orchestration) and let the user retry.
            if (this.streamTerminal) { this.closeStream(); return; }
            this.closeStream();
            this.recover();
            this.showToast("Stream interrupted — click Inject anomaly to retry.");
        });
    }

    closeStream() {
        if (this.es) { this.es.close(); this.es = null; }
    }

    // Re-enable the controls after a non-terminal failure so the operator can
    // relaunch the review manually (no background retries).
    recover() {
        document.getElementById("injectBtn").disabled = false;
    }

    agent(d, state) {
        const card = document.querySelector(`[data-agent="${d.agent}"]`);
        if (!card) return;
        card.setAttribute("data-status", state === "running" ? "running" : "");
        const dot = card.querySelector(".status-dot");
        const txt = card.querySelector(".status-text");
        dot.setAttribute("data-status", state);
        txt.textContent = state === "running" ? "Running" : "Done";
        if (state === "running" && d.message) this.log({ agent: d.agent, message: "▶ " + d.message });
    }

    log(d) {
        const card = document.querySelector(`[data-agent="${d.agent}"]`);
        if (!card) return;
        const box = card.querySelector(".agent-log");
        const line = document.createElement("div");
        line.textContent = d.message;
        box.appendChild(line);
        box.scrollTop = box.scrollHeight;
    }

    renderDiagnosis(d) {
        const el = document.getElementById("diagnosisCard");
        el.className = "result-card";
        const crit = String(d.criticality || "medium").toLowerCase();
        el.innerHTML =
            `<h4>${(d.failure_mode || "unknown").toUpperCase()} <span class="badge badge-${crit}">${crit}</span></h4>` +
            `<div class="kv"><span>Estimated RUL</span><span>${d.rul_days ?? "—"} days</span></div>` +
            `<div class="kv"><span>Confidence</span><span>${d.confidence != null ? Math.round(d.confidence * 100) + "%" : "—"}</span></div>` +
            `<div class="kv"><span>Rationale</span><span>${d.rationale || ""}</span></div>`;
    }

    renderSop(payload) {
        const d = payload.data || {};
        const el = document.getElementById("sopCard");
        el.className = "result-card";
        const steps = (d.key_steps || []).map((s) => `<li>${s}</li>`).join("");
        el.innerHTML =
            `<h4>${d.sop_id || d.doc_id || "SOP"} — ${d.title || ""}</h4>` +
            `<p>${d.summary || ""}</p>` +
            (steps ? `<ul class="steps">${steps}</ul>` : "") +
            `<div class="cite">📎 Cited source: ${d.citation || d.source || "n/a"}</div>`;
    }

    // ---------------------------------------------------------- approval
    showApproval(payload) {
        const p = payload.proposal;
        this.runId = payload.run_id || this.runId;
        const crit = String(p.criticality || "medium").toLowerCase();
        document.getElementById("proposalCard").innerHTML = [
            ["Asset", `${p.asset_id} — ${p.asset_model}`],
            ["Failure mode", p.failure_mode],
            ["Priority", `${p.priority} (${crit})`],
            ["Remaining useful life", `${p.rul_days ?? "—"} days`],
            ["Required skill", p.required_skill],
            ["SOP", `${p.sop_id} — ${p.sop_title}`],
        ].map(([k, v]) => `<div class="kv"><span>${k}</span><span>${v ?? "—"}</span></div>`).join("");
        const sec = document.getElementById("approvalSection");
        sec.classList.remove("hidden");
        sec.scrollIntoView({ behavior: "smooth", block: "center" });
        document.getElementById("injectBtn").disabled = false;
        this.setApprovalDisabled(false);
    }

    setApprovalDisabled(v) {
        document.getElementById("approveBtn").disabled = v;
        document.getElementById("rejectBtn").disabled = v;
    }

    async decide(decision) {
        if (!this.runId) return;
        this.setApprovalDisabled(true);
        const reason = document.getElementById("reasonInput").value;
        const res = await fetch("/api/approval", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ run_id: this.runId, decision, reason }),
        });
        if (!res.ok) { this.showToast("Approval failed."); this.setApprovalDisabled(false); return; }
        if (decision === "reject") {
            this.showToast("Dispatch rejected — decision logged for governance.");
            document.getElementById("approvalSection").classList.add("hidden");
            return;
        }
        this.dispatch();
    }

    dispatch() {
        document.getElementById("approvalSection").classList.add("hidden");
        const gen = ++this.streamGen;
        this.streamTerminal = false;
        this.es = new EventSource(`/api/dispatch?run_id=${this.runId}`);
        this.wireCommon(this.es, gen);
        this.es.addEventListener("work_order", (e) => {
            if (gen === this.streamGen) this.renderWorkOrder(JSON.parse(e.data).data);
        });
        this.es.addEventListener("done", () => {
            if (gen !== this.streamGen) return;
            this.streamTerminal = true;
            this.closeStream();
        });
    }

    renderWorkOrder(wo) {
        const sec = document.getElementById("workOrderSection");
        sec.classList.remove("hidden");
        const asg = wo.assignment || {};
        document.getElementById("workOrderCard").innerHTML =
            `<div class="wo-head"><span class="wo-id">${wo.work_order_id}</span>` +
            `<span class="badge badge-${(wo.priority === "P1" ? "high" : wo.priority === "P3" ? "low" : "medium")}">${wo.priority}</span></div>` +
            `<div class="kv"><span>Title</span><span>${wo.title}</span></div>` +
            `<div class="kv"><span>Asset</span><span>${wo.asset_id}</span></div>` +
            `<div class="kv"><span>SOP attached</span><span>${wo.sop_id || "—"}</span></div>` +
            `<div class="kv"><span>Technician</span><span>${wo.technician || "—"} ${asg.skill_matched === false ? "(nearest available)" : ""}</span></div>` +
            `<div class="kv"><span>Scheduled for</span><span>${wo.scheduled_for || "—"}</span></div>` +
            `<div class="kv"><span>Status</span><span>${wo.status}</span></div>` +
            `<div class="wo-summary">${wo.summary || ""}</div>`;
        sec.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    // ------------------------------------------------------------- reset
    resetAll() {
        // Invalidate any in-flight stream (its callbacks become no-ops) and
        // close the connection so it cannot auto-reconnect.
        this.streamGen++;
        this.streamTerminal = true;
        this.closeStream();
        this.runId = null;
        document.querySelectorAll(".agent-card").forEach((c) => {
            c.removeAttribute("data-status");
            c.querySelector(".status-dot").setAttribute("data-status", "idle");
            c.querySelector(".status-text").textContent = "Idle";
            c.querySelector(".agent-log").innerHTML = "";
        });
        const dc = document.getElementById("diagnosisCard");
        dc.className = "result-card muted"; dc.textContent = "Awaiting diagnosis…";
        const sc = document.getElementById("sopCard");
        sc.className = "result-card muted"; sc.textContent = "Awaiting knowledge retrieval…";
        document.getElementById("approvalSection").classList.add("hidden");
        document.getElementById("workOrderSection").classList.add("hidden");
        document.getElementById("reasonInput").value = "";
        document.getElementById("injectBtn").disabled = false;
    }

    showToast(msg) {
        this.toast.textContent = msg;
        this.toast.classList.add("show");
        setTimeout(() => this.toast.classList.remove("show"), 5000);
    }
}

document.addEventListener("DOMContentLoaded", () => new SignalToService());
