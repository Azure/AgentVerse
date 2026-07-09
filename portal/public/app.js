/* AgentVerse portal — catalog-driven tabbed SPA.
 *
 * Data sources:
 *   - catalog.json         : presentation metadata generated from each demo's
 *                            agentverse.yaml (baked into the image at build time).
 *   - window.__DEMOS__     : demo_id => public web URL, injected at runtime by the
 *                            container entrypoint from the DEMOS_JSON env var.
 * The two are linked by the demo id (catalog `name` === DEMOS_JSON key).
 */
(function () {
  "use strict";

  var DEMO_URLS = window.__DEMOS__ || {};
  var FRAME_TIMEOUT_MS = 7000;

  var tabsEl = document.getElementById("tabs");
  var panelEl = document.getElementById("panel");
  var emptyEl = document.getElementById("empty");
  var countEl = document.getElementById("demo-count");

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // Merge catalog metadata with the injected URL map into one demo list.
  function buildDemos(catalog) {
    var byId = {};
    (catalog.demos || []).forEach(function (d) {
      byId[d.name] = {
        id: d.name,
        title: d.title || d.name,
        tagline: d.tagline || "",
        status: d.status || "",
        orchestration: d.orchestration || "",
        agents: d.agents || [],
        tags: d.tags || [],
        stack: d.stack || {},
        url: DEMO_URLS[d.name] || null,
      };
    });
    // Deployed demos without catalog metadata still get a minimal tab.
    Object.keys(DEMO_URLS).forEach(function (id) {
      if (!byId[id]) {
        byId[id] = { id: id, title: id, tagline: "", agents: [], tags: [], stack: {}, url: DEMO_URLS[id] };
      }
    });
    return Object.keys(byId)
      .sort()
      .map(function (k) { return byId[k]; });
  }

  function renderTabs(demos, activeId, onSelect) {
    tabsEl.innerHTML = "";
    demos.forEach(function (d) {
      var t = el("button", "tab" + (d.id === activeId ? " active" : ""));
      var dot = el("span", "dot " + (d.url ? "up" : "down"));
      t.appendChild(dot);
      t.appendChild(document.createTextNode(d.title));
      t.title = d.url ? "Deployed" : "Not deployed";
      t.onclick = function () { onSelect(d.id); };
      tabsEl.appendChild(t);
    });
  }

  function renderPanel(demo) {
    panelEl.innerHTML = "";

    var head = el("div", "demo-head");
    var left = el("div");
    left.appendChild(el("h2", "demo-title", demo.title));
    if (demo.tagline) left.appendChild(el("p", "demo-tagline", demo.tagline));

    var meta = el("div", "demo-meta");
    if (demo.orchestration) meta.appendChild(el("span", "chip", demo.orchestration));
    (demo.agents || []).forEach(function (a) {
      meta.appendChild(el("span", "chip", a.name || a));
    });
    (demo.tags || []).forEach(function (tag) {
      meta.appendChild(el("span", "chip muted", tag));
    });
    left.appendChild(meta);
    head.appendChild(left);

    var actions = el("div", "actions");
    if (demo.url) {
      var open = el("a", "btn primary", "Open in new tab");
      open.href = demo.url;
      open.target = "_blank";
      open.rel = "noopener";
      actions.appendChild(open);
    }
    head.appendChild(actions);
    panelEl.appendChild(head);

    var wrap = el("div", "frame-wrap");
    if (demo.url) {
      var frame = el("iframe");
      frame.src = demo.url;
      frame.setAttribute("allow", "clipboard-write; microphone");
      frame.setAttribute("referrerpolicy", "no-referrer");

      var fallback = el("div", "frame-fallback hidden");
      fallback.appendChild(el("h3", null, "Can't display this demo here"));
      var p = el("p", null,
        "The demo may block embedding (X-Frame-Options / CSP) or require a sign-in " +
        "flow that doesn't work inside a frame. Open it directly instead.");
      fallback.appendChild(p);
      var openBtn = el("a", "btn primary", "Open the demo");
      openBtn.href = demo.url;
      openBtn.target = "_blank";
      openBtn.rel = "noopener";
      fallback.appendChild(openBtn);

      var loaded = false;
      frame.addEventListener("load", function () { loaded = true; });
      // If the frame never loads (blocked/slow), reveal the fallback.
      setTimeout(function () {
        if (!loaded) fallback.classList.remove("hidden");
      }, FRAME_TIMEOUT_MS);

      wrap.appendChild(frame);
      wrap.appendChild(fallback);
    } else {
      var nd = el("div", "frame-fallback");
      nd.appendChild(el("h3", null, "Not deployed"));
      nd.appendChild(el("p", null,
        "This demo has catalog metadata but no deployed URL. Enable it in " +
        "demos.auto.tfvars and re-apply the global Terraform."));
      wrap.appendChild(nd);
    }
    panelEl.appendChild(wrap);
  }

  function main(catalog) {
    var demos = buildDemos(catalog);
    countEl.textContent = demos.length + " demo" + (demos.length === 1 ? "" : "s");

    if (demos.length === 0) {
      emptyEl.classList.remove("hidden");
      return;
    }

    var active = demos[0].id;
    function select(id) {
      active = id;
      var demo = demos.filter(function (d) { return d.id === id; })[0];
      renderTabs(demos, active, select);
      renderPanel(demo);
    }
    select(active);
  }

  fetch("catalog.json", { cache: "no-store" })
    .then(function (r) { return r.ok ? r.json() : { demos: [] }; })
    .catch(function () { return { demos: [] }; })
    .then(main);
})();
