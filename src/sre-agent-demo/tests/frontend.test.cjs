"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.classList = { add() {}, toggle() {} };
  }
  set innerHTML(value) { this.children = []; this.html = value; }
  appendChild(child) { child.parent = this; this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  click() { return this.listeners.click?.(); }
  remove() { this.parent.children = this.parent.children.filter((child) => child !== this); }
}

function fixture(id = "test", kind = "pr") {
  const draft = {
    kind, title: `<script>${id}</script>`,
    repository: `example-org/${id}`, reviewer: "Platform maintainers",
    approval_status: "Not requested", disclaimer: "Illustrative only",
    filename: `${id}-${kind}-draft.md`, markdown: `# ${id}\n\nSimulated evidence.\n`,
  };
  return {
    id, title: id, summary: "Simulated", mode: "Review",
    signal: { source: "Replay", fired_at: "12:00" },
    turns: [
      { role: "signal", title: "Signal" },
      { role: "approval", title: "Review", action: "Proposed only" },
      { role: "resolution", title: "Expected only" },
      { role: "repository", title: "Repository follow-up", draft },
    ],
  };
}

function descendants(node) {
  return node.children.flatMap((child) => [child, ...descendants(child)]);
}

async function harness() {
  const nodes = new Map();
  const requests = [];
  const blobs = [];
  const links = [];
  const revoked = [];
  let fetchScenario = async (id) => fixture(id);
  const document = {
    body: new Element("body"),
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, new Element("div"));
      return nodes.get(id);
    },
    createElement(tag) {
      const element = new Element(tag);
      if (tag === "a") links.push(element);
      return element;
    },
    querySelectorAll() { return []; },
  };
  const context = vm.createContext({
    document, Blob,
    URL: {
      createObjectURL(blob) { blobs.push(blob); return "blob:local"; },
      revokeObjectURL(url) { revoked.push(url); },
    },
    setTimeout(callback) { callback(); },
    setInterval() { return 1; }, clearInterval() {},
    async fetch(url) {
      requests.push(url);
      let payload;
      if (url === "/api/config") payload = { mode: "replay" };
      else if (url === "/api/scenarios") payload = { scenarios: [] };
      else if (url === "/api/context") payload = {};
      else payload = await fetchScenario(decodeURIComponent(url.split("/").pop()));
      return { ok: true, json: async () => payload };
    },
  });
  const source = fs.readFileSync(path.join(__dirname, "..", "app", "frontend", "app.js"), "utf8");
  vm.runInContext(source, context);
  await new Promise(setImmediate);
  return {
    nodes, requests, blobs, links, revoked, context,
    run: (code) => vm.runInContext(code, context),
    setFetch(callback) { fetchScenario = callback; },
  };
}

test("the draft is revealed only at the end; export matches preview and stays local", async () => {
  const h = await harness();
  await h.run("selectScenario('test')");
  assert.equal(h.nodes.get("timeline").children.length, 1);
  assert.equal(descendants(h.nodes.get("timeline")).some((n) => n.tagName === "details"), false);
  h.run("showAll()");
  const turns = h.nodes.get("timeline").children;
  assert.equal(turns.length, 4);
  const cardNodes = descendants(turns[3]);
  const preview = cardNodes.find((n) => n.className === "draft-preview");
  const download = cardNodes.find((n) => n.tagName === "button");
  assert.equal(preview.textContent, fixture().turns[3].draft.markdown);
  assert.equal(cardNodes.find((n) => n.tagName === "h3").textContent, "<script>test</script>");
  download.click();
  assert.equal(await h.blobs[0].text(), preview.textContent);
  assert.equal(h.links.at(-1).download, "test-pr-draft.md");
  assert.equal(h.links.at(-1).href, "blob:local");
  assert.deepEqual(h.revoked, ["blob:local"]);
  assert.ok(h.requests.every((url) => url.startsWith("/api/")));
  const approvals = descendants(turns[1]).filter((n) => n.tagName === "button");
  assert.ok(approvals.every((n) => n.disabled));
  assert.equal(approvals.length, 2);
});

test("reset and incident changes remove stale drafts; step and play still work", async () => {
  const h = await harness();
  await h.run("selectScenario('first')");
  h.run("showAll(); resetTimeline()");
  assert.equal(h.nodes.get("timeline").children.length, 1);
  assert.equal(h.run("state.revealed"), 1);
  h.run("startPlay()");
  assert.equal(h.run("state.timer"), 1);
  await h.run("selectScenario('second')");
  assert.equal(h.run("state.timer"), null);
  h.run("revealNext(); revealNext(); revealNext()");
  const preview = descendants(h.nodes.get("timeline")).find((n) => n.className === "draft-preview");
  assert.equal(preview.textContent, fixture("second").turns[3].draft.markdown);
});

test("a slower selection cannot overwrite the current incident or its draft", async () => {
  const h = await harness();
  let release;
  h.setFetch((id) => id === "slow" ? new Promise((resolve) => { release = resolve; }) : fixture(id));
  const slow = h.run("selectScenario('slow')");
  await h.run("selectScenario('fast')");
  h.run("showAll()");
  release(fixture("slow"));
  await slow;
  assert.equal(h.run("state.scenario.id"), "fast");
  assert.equal(h.nodes.get("timeline").children.length, 4);
});

test("load failures clear the old draft and surface an error", async () => {
  const h = await harness();
  await h.run("selectScenario('first')");
  h.run("showAll()");
  h.setFetch(async () => { throw new Error("offline"); });
  await h.run("selectScenario('broken')");
  assert.equal(h.nodes.get("timeline").children.length, 0);
  assert.equal(h.nodes.get("inv-title").textContent, "Failed to load incident.");
  assert.equal(h.nodes.get("inv-summary").textContent, "offline");
});

test("issue export failures are visible and do not claim publication", async () => {
  const h = await harness();
  h.setFetch(async () => fixture("capacity", "issue"));
  await h.run("selectScenario('capacity')");
  h.run("showAll()");
  h.run("URL.createObjectURL = () => { throw new Error('download blocked'); }");
  const cardNodes = descendants(h.nodes.get("timeline").children[3]);
  cardNodes.find((n) => n.tagName === "button").click();
  assert.equal(cardNodes.find((n) => n.role === "status").textContent,
    "Unable to download draft: download blocked");
  assert.equal(h.blobs.length, 0);
});
