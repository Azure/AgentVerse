/* AgentVerse portal — catalog-driven SPA with a landing page + one tab per demo.
 *
 * Data sources:
 *   - catalog.json         : presentation metadata generated from each demo's
 *                            agentverse.yaml (baked into the image at build time).
 *   - window.__DEMOS__     : demo_id => public web URL, injected at runtime by the
 *                            container entrypoint from the DEMOS_JSON env var.
 * The two are linked by the demo id (catalog `name` === DEMOS_JSON key).
 *
 * Views: the landing page (HOME_VIEW) is shown first and lists every catalog demo
 * as a card; selecting a card or a tab opens that demo's embedded frontend. Any
 * new demo added to the catalog automatically gets both a card and a tab.
 */
(function () {
  "use strict";

  var DEMO_URLS = window.__DEMOS__ || {};
  var FRAME_TIMEOUT_MS = 7000;
  var HOME_VIEW = "__home__";

  var tabsEl = document.getElementById("tabs");
  var panelEl = document.getElementById("panel");
  var homeEl = document.getElementById("home");
  var gridEl = document.getElementById("demo-grid");
  var emptyEl = document.getElementById("empty");
  var countEl = document.getElementById("demo-count");
  var stageEl = document.getElementById("stage");
  var brandEl = document.getElementById("brand");

  var demos = [];
  var active = HOME_VIEW;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function titleCase(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
  }

  // Merge catalog metadata with the injected URL map into one demo list.
  function buildDemos(catalog) {
    var byId = {};
    (catalog.demos || []).forEach(function (d) {
      byId[d.name] = {
        id: d.name,
        title: d.title || d.name,
        tagline: d.tagline || "",
        description: d.description || "",
        status: d.status || "",
        orchestration: d.orchestration || "",
        agents: Array.isArray(d.agents) ? d.agents : [],
        tags: Array.isArray(d.tags) ? d.tags : [],
        models: Array.isArray(d.models) ? d.models : [],
        stack: d.stack || {},
        url: DEMO_URLS[d.name] || null,
      };
    });
    // Deployed demos without catalog metadata still get a minimal entry.
    Object.keys(DEMO_URLS).forEach(function (id) {
      if (!byId[id]) {
        byId[id] = {
          id: id, title: id, tagline: "", description: "", status: "",
          orchestration: "", agents: [], tags: [], models: [], stack: {}, url: DEMO_URLS[id],
        };
      }
    });
    return Object.keys(byId)
      .sort()
      .map(function (k) { return byId[k]; });
  }

  // A restrained status badge for a demo card.
  function statusMeta(demo) {
    if (!demo.url) return { cls: "badge muted", label: "Not deployed" };
    var s = (demo.status || "").toLowerCase();
    if (s === "stable") return { cls: "badge ok", label: "Stable" };
    if (s === "beta") return { cls: "badge info", label: "Beta" };
    if (s === "experimental") return { cls: "badge warn", label: "Experimental" };
    return { cls: "badge info", label: s ? titleCase(s) : "Live" };
  }

  function findDemo(id) {
    for (var i = 0; i < demos.length; i++) {
      if (demos[i].id === id) return demos[i];
    }
    return null;
  }

  /* ---- Tabs ------------------------------------------------------------- */
  function renderTabs() {
    tabsEl.innerHTML = "";

    var homeTab = el("button", "tab" + (active === HOME_VIEW ? " active" : ""), "Home");
    homeTab.type = "button";
    if (active === HOME_VIEW) homeTab.setAttribute("aria-current", "page");
    homeTab.onclick = function () { select(HOME_VIEW); };
    tabsEl.appendChild(homeTab);

    demos.forEach(function (d) {
      var t = el("button", "tab" + (d.id === active ? " active" : ""));
      t.type = "button";
      var dot = el("span", "dot " + (d.url ? "up" : "down"));
      t.appendChild(dot);
      t.appendChild(document.createTextNode(d.title));
      t.title = d.url ? "Deployed" : "Not deployed";
      if (d.id === active) t.setAttribute("aria-current", "page");
      t.onclick = function () { select(d.id); };
      tabsEl.appendChild(t);
    });
  }

  /* ---- Landing page ----------------------------------------------------- */
  function renderHome() {
    gridEl.innerHTML = "";
    demos.forEach(function (d) {
      var row = el("article", "demo-row");

      /* --- main column: identity + full description + metadata --- */
      var main = el("div", "row-main");

      var head = el("div", "row-head");
      head.appendChild(el("h3", "row-title", d.title));
      var sm = statusMeta(d);
      head.appendChild(el("span", sm.cls, sm.label));
      main.appendChild(head);

      if (d.tagline) main.appendChild(el("p", "row-tagline", d.tagline));
      main.appendChild(el("p", "row-desc",
        d.description || d.tagline || "No description available yet."));

      // Meta pills: orchestration, agent count, then a few distinguishing tags.
      var meta = el("div", "row-meta");
      if (d.orchestration) meta.appendChild(el("span", "tagpill", d.orchestration));
      if (d.agents.length) {
        meta.appendChild(el("span", "tagpill",
          d.agents.length + " agent" + (d.agents.length === 1 ? "" : "s")));
      }
      var orch = (d.orchestration || "").toLowerCase();
      d.tags.filter(function (tag) { return tag.toLowerCase() !== orch; })
        .slice(0, 4)
        .forEach(function (tag) {
          meta.appendChild(el("span", "tagpill muted", tag));
        });
      if (meta.childNodes.length) main.appendChild(meta);

      row.appendChild(main);

      /* --- side column: models + launch actions --- */
      var side = el("div", "row-side");

      if (d.models.length) {
        var modelsBlock = el("div", "row-models");
        modelsBlock.appendChild(el("span", "row-models-label", "Models"));
        var chips = el("div", "model-chips");
        d.models.forEach(function (m) {
          chips.appendChild(el("span", "model-chip", m));
        });
        modelsBlock.appendChild(chips);
        side.appendChild(modelsBlock);
      }

      var actions = el("div", "row-actions");
      var openBtn = el("button", "btn primary", d.url ? "Open demo" : "View details");
      openBtn.type = "button";
      openBtn.onclick = function () { select(d.id); };
      actions.appendChild(openBtn);
      if (d.url) {
        var ext = el("a", "btn ghost", "Open in new tab \u2197");
        ext.href = d.url;
        ext.target = "_blank";
        ext.rel = "noopener";
        actions.appendChild(ext);
      }
      side.appendChild(actions);

      row.appendChild(side);
      gridEl.appendChild(row);
    });
  }

  /* ---- Demo panel (iframe) ---------------------------------------------- */
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
      fallback.appendChild(el("p", null,
        "The demo may block embedding (X-Frame-Options / CSP) or require a sign-in " +
        "flow that doesn't work inside a frame. Open it directly instead."));
      var openBtn = el("a", "btn primary", "Open the demo");
      openBtn.href = demo.url;
      openBtn.target = "_blank";
      openBtn.rel = "noopener";
      fallback.appendChild(openBtn);

      var loaded = false;
      frame.addEventListener("load", function () { loaded = true; });
      // If the frame never loads (blocked/slow), reveal the fallback — but only
      // if this panel is still mounted (guards against a stale timeout firing
      // after the user switched to another view).
      setTimeout(function () {
        if (!loaded && document.contains(fallback)) fallback.classList.remove("hidden");
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

  /* ---- Navigation ------------------------------------------------------- */
  function select(view) {
    if (view !== HOME_VIEW && !findDemo(view)) view = HOME_VIEW;
    active = view;
    renderTabs();

    if (view === HOME_VIEW) {
      panelEl.classList.add("hidden");
      homeEl.classList.remove("hidden");
      stageEl.classList.add("home-mode");
      renderHome();
      stageEl.scrollTop = 0;
    } else {
      homeEl.classList.add("hidden");
      panelEl.classList.remove("hidden");
      stageEl.classList.remove("home-mode");
      renderPanel(findDemo(view));
    }
    setHash(view);
  }

  /* ---- Minimal hash routing (shareable deep links) ---------------------- */
  function viewFromHash() {
    var h = (location.hash || "").replace(/^#/, "");
    if (!h || h === "home") return HOME_VIEW;
    if (h.indexOf("demo-") === 0) {
      var id = decodeURIComponent(h.slice(5));
      if (findDemo(id)) return id;
    }
    return HOME_VIEW;
  }

  function setHash(view) {
    var h = view === HOME_VIEW ? "home" : "demo-" + encodeURIComponent(view);
    if (location.hash !== "#" + h) location.hash = h;
  }

  function main(catalog) {
    demos = buildDemos(catalog);
    countEl.textContent = demos.length + " demo" + (demos.length === 1 ? "" : "s");

    if (demos.length === 0) {
      homeEl.classList.add("hidden");
      panelEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    brandEl.addEventListener("click", function () { select(HOME_VIEW); });
    window.addEventListener("hashchange", function () {
      var v = viewFromHash();
      if (v !== active) select(v);
    });

    select(viewFromHash());
  }

  fetch("catalog.json", { cache: "no-store" })
    .then(function (r) { return r.ok ? r.json() : { demos: [] }; })
    .catch(function () { return { demos: [] }; })
    .then(main);
})();
