"""Build the public, dependency-light AgentVerse site from validated manifests."""
from __future__ import annotations

import argparse
import importlib.util
import json
from html import escape
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = "https://github.com/Azure/AgentVerse"
SOURCE = f"{REPO}/tree/main/"
THEME_SCRIPT = """(() => {
    const param = new URLSearchParams(window.location.search).get("scoutTheme");
    const theme =
      param || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  })();"""


def text(value: object) -> str:
    return escape(str(value), quote=True)


def source_link(path: str) -> str:
    return SOURCE + quote(path, safe="/#")


def load_catalog() -> list[dict]:
    spec = importlib.util.spec_from_file_location(
        "catalog_builder", ROOT / "src" / "templates" / "catalog" / "build_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entries, failed = module.build_index(module.load_schema())
    if failed or not entries:
        raise ValueError("Cannot publish: demo manifests are invalid or missing.")
    return entries


def load_stories(entries: list[dict]) -> dict:
    stories = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    expected = {entry["name"] for entry in entries}
    if stories.keys() != expected:
        raise ValueError(
            f"Scenario copy must match manifests. Missing: {expected - stories.keys()}; "
            f"unknown: {stories.keys() - expected}"
        )
    string_fields = ("industry", "headline", "summary", "problem", "outcome", "reality", "start_path")
    for name, story in stories.items():
        for field in string_fields:
            if not isinstance(story.get(field), str) or not story[field].strip():
                raise ValueError(f"{name}: {field} must be non-empty text.")
        for field in ("steps", "prerequisites"):
            values = story.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise ValueError(f"{name}: {field} must be a non-empty text list.")
        start = (ROOT / story["start_path"].split("#")[0]).resolve()
        if not start.is_relative_to(ROOT / "src") or not start.is_file():
            raise ValueError(f"{name}: quickstart must reference an existing source document.")
    return stories


def page(title: str, description: str, body: str, active: str = "", depth: int = 0) -> str:
    base = "../" * depth or "./"
    nav = "".join(
        f'<a href="{base}{url}"'
        + (' aria-current="page"' if key == active else "")
        + f">{label}</a>"
        for key, url, label in (
            ("explore", "explore.html", "Explore scenarios"),
            ("blocks", "building-blocks.html", "Building blocks"),
            ("start", "get-started.html", "Get started"),
            ("about", "about.html", "About AgentVerse"),
        )
    )
    css = (HERE / "styles.css").read_text(encoding="utf-8")
    js = (HERE / "site.js").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(title)} | AgentVerse</title>
  <meta name="description" content="{text(description)}">
  <meta property="og:title" content="{text(title)} | AgentVerse">
  <meta property="og:description" content="{text(description)}">
  <meta property="og:type" content="website">
  <script>{THEME_SCRIPT}</script>
  <style>{css}</style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header"><div class="wrap header-inner">
    <a class="brand" href="{base}index.html" aria-label="AgentVerse home">
      <span class="brand-mark" aria-hidden="true">A<span></span></span>AgentVerse<span class="brand-label"> / examples to build on</span>
    </a>
    <nav aria-label="Main navigation">{nav}</nav>
    <button class="theme-toggle" type="button" aria-label="Switch color theme" hidden>Theme</button>
  </div></header>
  <main id="main">{body}</main>
  <footer class="site-footer"><div class="wrap footer-inner">
    <div><a class="brand" href="{base}index.html">AgentVerse</a>
    <p>Practical examples. A starting point, not a finished product.</p></div>
    <nav aria-label="Footer">
      <a href="{REPO}">Source on GitHub &#8599;</a>
      <a href="{REPO}#contributing">Contribute</a>
      <a href="https://privacy.microsoft.com/privacystatement">Privacy</a>
      <a href="{REPO}/blob/main/LICENSE">License</a>
    </nav>
  </div></footer>
  <script>{js}</script>
</body>
</html>
"""


def workflow(steps: list[str], compact: bool = False) -> str:
    return '<ol class="workflow' + (" compact" if compact else "") + '">' + "".join(
        f'<li><span class="step-index" aria-hidden="true">{index:02}</span><span>{text(step)}</span></li>'
        for index, step in enumerate(steps, 1)
    ) + "</ol>"


def card(entry: dict, story: dict) -> str:
    name = entry["name"]
    search = " ".join([
        entry["title"], story["headline"], story["summary"], story["industry"],
        *entry.get("tags", []), *entry.get("capabilities", []),
    ])
    return f"""<article class="scenario-card" data-scenario data-search="{text(search.lower())}"
      data-industry="{text(story['industry'])}" data-difficulty="{text(entry.get('difficulty', ''))}">
      <div class="card-top"><span class="eyebrow">{text(story['industry'])}</span>
      <span class="status">{text(entry['status'])}</span></div>
      <h3><a href="scenarios/{text(name)}.html">{text(story['headline'])}</a></h3>
      <p>{text(story['summary'])}</p>
      <div class="card-bottom"><span>{text(entry['title'])}</span>
        <span class="card-arrow" aria-hidden="true">&#8599;</span></div>
    </article>"""


def hero_carousel(entries: list[dict], stories: dict) -> str:
    slides = ""
    dots = ""
    for index, entry in enumerate(entries):
        story = stories[entry["name"]]
        stages = "".join(
            f'<div><span aria-hidden="true">{step_index:02}</span><strong>{text(step)}</strong></div>'
            for step_index, step in enumerate(story["steps"][:3], 1)
        )
        checkpoint = " ".join(story["steps"][3:])
        slides += f"""<div class="hero-slide" id="hero-slide-{index}" role="group"
          aria-roledescription="slide" aria-label="{index + 1} of {len(entries)}: {text(entry['title'])}">
          <div class="art-heading"><span class="eyebrow">{text(entry['title'])}</span>
          <span class="status">Illustrative</span></div>
          <div class="art-request"><span class="eyebrow">A real-world need</span><p>{text(story['headline'])}</p></div>
          <div class="art-agents">{stages}</div>
          <div class="art-approval"><span class="approval-dot" aria-hidden="true"></span>{text(checkpoint)}</div>
          <div class="art-result"><span class="eyebrow">What this example shows</span><strong>{text(story['outcome'])}</strong>
          <a href="scenarios/{text(entry['name'])}.html">Explore this scenario <span aria-hidden="true">&#8594;</span></a></div>
        </div>"""
        dots += f'<button type="button" class="slide-dot" data-slide="{index}" aria-label="Show {text(entry["title"])}" aria-controls="hero-slide-{index}"><span aria-hidden="true"></span></button>'
    return f"""<section class="hero-art" aria-label="Explore agentic workflows" aria-roledescription="carousel">
      <div class="carousel-heading"><span class="eyebrow">Inside an agentic workflow</span>
      <span class="carousel-count" aria-live="polite" aria-atomic="true" hidden>1 / {len(entries)}</span></div>
      <div class="hero-slides">{slides}</div>
      <div class="carousel-controls" hidden>
        <button type="button" class="carousel-arrow" data-direction="-1" aria-label="Previous scenario">&#8592;</button>
        <div class="carousel-dots" role="group" aria-label="Choose a scenario">{dots}</div>
        <button type="button" class="carousel-arrow" data-direction="1" aria-label="Next scenario">&#8594;</button>
      </div>
      <noscript><p class="carousel-hint">Scroll horizontally through the examples to explore each workflow.</p></noscript>
    </section>"""


def home(entries: list[dict], stories: dict) -> str:
    by_name = {entry["name"]: entry for entry in entries}
    featured = ("foundryairlines-demo", "insurance-ai-agents", "signal-to-service")
    cards = "".join(card(by_name[name], stories[name]) for name in featured if name in by_name)
    return f"""<section class="hero wrap">
      <div class="hero-copy"><p class="eyebrow">Real problems. Agentic possibilities.</p>
      <h1>Start building<br>with <em>AI agents.</em></h1>
      <p class="lede">Go from &ldquo;what could agents do?&rdquo; to &ldquo;here&rsquo;s how we could build it.&rdquo;
      Explore examples based on real customer use cases being used or deployed in large enterprises,
      understand how they work, and make them your own.</p>
      <div class="actions"><a class="button primary" href="explore.html">Explore scenarios <span aria-hidden="true">&#8599;</span></a>
      <a class="button secondary" href="get-started.html">Find your starting point</a></div>
      <p class="hero-note">Open source &middot; Built within Microsoft &middot; Yours to adapt</p></div>
      {hero_carousel(entries, stories)}
    </section>
    <div class="proof-strip"><div class="wrap proof-inner">
      <span><strong>{len(entries):02}</strong> scenarios to explore</span>
      <span>Business context <strong aria-hidden="true">/</strong> Working code <strong aria-hidden="true">/</strong> Deployment guidance</span>
      <a href="{REPO}">Open on GitHub &#8599;</a>
    </div></div>
    <section class="section wrap intro-grid"><div><p class="eyebrow">Beyond a chatbot</p><h2>Agents do more than answer.<br>They help get work done.</h2></div>
      <div><p class="lede small">An AI agent combines a model with instructions and tools to work toward a goal.
      Several agents can share a task, bring in relevant information, and involve a person when a decision needs review.</p>
      <p>AgentVerse makes those ideas concrete. The public demos make real customer scenarios accessible
      through reference code, sample data, and, where noted, simulated or replayed workflows.</p>
      <p>Microsoft Agent Framework brings reusable agent, tool, and workflow building blocks to the
      Framework-based examples, so teams can spend less time wiring components together and more time
      adapting the business process.</p>
      <p>All examples can be co-built with Microsoft staff if you need help getting started or adapting
      them to your enterprise. <a href="get-started.html#co-build">Explore co-building with Microsoft</a>.</p>
      <a class="text-link" href="about.html">Who it&rsquo;s for and why we built it &#8594;</a></div></section>
    <section class="section wrap"><div class="section-heading"><div><p class="eyebrow">A few places to begin</p>
      <h2>Real scenarios.<br>Reusable ideas.</h2></div><a class="text-link" href="explore.html">View all {len(entries)} scenarios &#8594;</a></div>
      <div class="card-grid">{cards}</div></section>
    <section class="section wrap"><div class="journey-panel"><p class="eyebrow">From curiosity to your first build</p>
      <h2>You don&rsquo;t have to start from scratch.</h2>
      <div class="journey-grid"><div><span class="step-index">01</span><h3>Discover</h3><p>Find a problem that looks like yours. See where agents can help.</p></div>
      <div><span class="step-index">02</span><h3>Understand</h3><p>Follow the workflow. See the tools, decisions, and human checkpoints.</p></div>
      <div><span class="step-index">03</span><h3>Build on it</h3><p>Run an example, adapt the code, and evaluate it for your own needs.</p></div></div>
      <a class="button primary" href="get-started.html">Get started &#8594;</a></div></section>"""


def about() -> str:
    return f"""<section class="page-hero wrap"><p class="eyebrow">About AgentVerse</p>
      <h1>A shared starting point.<br><em>Built for you to build on.</em></h1>
      <p class="lede">Examples based on real customer use cases being used or deployed in large enterprises,
      developed with Microsoft teams to help you
      understand what AI agents can do&mdash;and start creating your own solutions.</p>
      <div class="actions"><a class="button secondary" href="#who-is-this-for">Who is this for? &#8595;</a>
      <a class="button secondary" href="#why-agentverse">Why did we build it? &#8595;</a></div></section>
    <section class="section wrap" id="who-is-this-for" aria-labelledby="audience-title">
      <div class="section-heading"><div><p class="eyebrow">Different roles. A shared starting point.</p>
      <h2 id="audience-title">Who is AgentVerse for?</h2></div>
      <p class="section-description">Whether you&rsquo;re exploring an opportunity or writing the code,
      there&rsquo;s a way to start here.</p></div>
      <div class="audience-grid">
        <article class="audience-card"><span class="step-index" aria-hidden="true">01 / EXPLORE</span>
        <h3>Business &amp; innovation teams</h3>
        <p>Understand what agents could do for your organization. Start with a familiar problem and see
        the workflow, the people involved, and its limitations&mdash;without needing to read code.</p>
        <a class="text-link" href="explore.html">Explore the business scenarios &#8594;</a></article>
        <article class="audience-card"><span class="step-index" aria-hidden="true">02 / BUILD</span>
        <h3>Developers &amp; AI engineers</h3>
        <p>Get a concrete starting point instead of a blank project. Inspect the code, run an example,
        and adapt its agents, tools, and evaluations to your own use case.</p>
        <a class="text-link" href="get-started.html">Start your first build &#8594;</a></article>
        <article class="audience-card"><span class="step-index" aria-hidden="true">03 / DESIGN</span>
        <h3>Solution architects</h3>
        <p>Explore how the pieces fit together. Compare coordination patterns, grounding,
        and human checkpoints before deciding what belongs in your own solution.</p>
        <a class="text-link" href="building-blocks.html">Understand the building blocks &#8594;</a></article>
        <article class="audience-card"><span class="step-index" aria-hidden="true">04 / OPERATE</span>
        <h3>Platform &amp; operations teams</h3>
        <p>Look beyond the happy path. Use the examples to explore deployment, identity,
        observability, and governance&mdash;then assess what your environment needs.</p>
        <a class="text-link" href="scenarios/insurance-ai-agents.html">Explore a governed workflow &#8594;</a></article>
      </div>
    </section>
    <section class="section wrap" id="why-agentverse" aria-labelledby="purpose-title">
      <div class="purpose-panel"><div><p class="eyebrow">Why we built this</p>
      <h2 id="purpose-title">Make the first step<br>easier to take.</h2>
      <p class="lede small">Understanding the promise of AI agents is one thing.
      Knowing where to start building is another.</p></div>
      <div><p>AgentVerse brings together agentic use cases developed through collaboration across
      Microsoft teams and customers. The examples are based on real customer use cases being used or
      deployed in large enterprises, not just hypothetical business problems.</p>
      <p>We make those scenarios accessible through public reference implementations you can explore,
      run in your own environment, and adapt. Sample data, simulations, and replay modes let you
      understand a workflow without accessing a customer&rsquo;s systems. The public code is not a
      representation of every component in a customer deployment.</p>
      <p>The aim is to shorten the distance between an idea and a working starting point:
      connect technology to a real business problem, show how the solution fits together, and share
      reusable code rather than leave you with a concept alone.</p>
      <p><strong>Built to accelerate your start, not replace your engineering.</strong>
      These examples are not finished products or a substitute for your own security review,
      evaluation, and production design.</p>
      <a class="text-link" href="{REPO}#contributing">Build on it. Share what you learn. &#8599;</a></div></div>
    </section>
    <section class="wrap section"><div class="start-grid">
      <article class="setup-panel"><p class="eyebrow">Build together</p><h2>Microsoft staff can help you co-build.</h2>
      <p>All examples can be co-built with Microsoft staff if needed. Bring your business problem and
      work with your Microsoft team to discuss the scenario, integration needs, and next steps.</p>
      <a class="text-link" href="get-started.html#co-build">How to start a co-build conversation &#8594;</a></article>
      <article class="setup-panel"><p class="eyebrow">A reusable foundation</p><h2>Microsoft Agent Framework</h2>
      <p>The Framework-based demos use a common foundation for agents, tools, and multi-agent workflows.
      This helps make coordination explicit and components easier to reuse as you adapt a scenario.</p>
      <a class="text-link" href="building-blocks.html#agent-framework">See the value of the Framework &#8594;</a></article>
    </div></section>"""


def explore(entries: list[dict], stories: dict) -> str:
    industries = sorted({story["industry"] for story in stories.values()})
    options = "".join(f'<option>{text(industry)}</option>' for industry in industries)
    cards = "".join(card(entry, stories[entry["name"]]) for entry in entries)
    return f"""<section class="page-hero wrap"><p class="eyebrow">The scenario collection</p>
      <h1>Find your<br><em>starting point.</em></h1>
      <p class="lede">Start with a business need, not a technology. Each example shows what agents can do,
      how they work, and what it takes to build on them.</p>
      <p>Based on real customer use cases being used or deployed in large enterprises.
      Public demos retain the sample data and simulation boundaries described on each scenario page.</p>
      <a class="text-link" href="get-started.html#co-build">All examples can be co-built with Microsoft staff &#8594;</a></section>
    <section class="wrap catalog-section" aria-label="Scenario catalog">
      <form class="filters" role="search" hidden>
      <div class="filter-field search-field"><label for="scenario-search">Search scenarios</label><input id="scenario-search" type="search" name="q" placeholder="Try maintenance, voice, or governance"></div>
      <div class="filter-field"><label for="scenario-industry">Industry</label><select id="scenario-industry" name="industry"><option value="">All industries</option>{options}</select></div>
      <div class="filter-field"><label for="scenario-difficulty">Technical level</label><select id="scenario-difficulty" name="difficulty"><option value="">All levels</option>
      <option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></div>
      <button class="button secondary" type="reset">Clear filters</button></form>
      <noscript><p>All scenarios are shown below. Enable JavaScript to search and filter.</p></noscript>
      <p id="result-count" class="result-count" role="status" aria-live="polite">{len(entries)} scenarios</p>
      <div class="card-grid">{cards}</div>
      <div id="no-results" class="empty-state" hidden><h2>No matching scenarios</h2>
      <p>Try a broader keyword or clear the filters to see the full collection.</p></div>
      <p class="catalog-note">These are reference implementations, not production guarantees.
      Each scenario explains its current scope and limitations.</p>
    </section>"""


def scenario(entry: dict, story: dict) -> str:
    quickstart = source_link(story["start_path"])
    code = source_link("src/" + entry["_path"])
    agents = "".join(
        f'<li><strong>{text(agent["name"])}</strong><p>{text(agent["role"])}</p></li>'
        for agent in entry["agents"]
    )
    prerequisites = "".join(f"<li>{text(item)}</li>" for item in story["prerequisites"])
    services = "".join(f'<span class="chip">{text(service)}</span>' for service in entry.get("azureServices", []))
    stack = entry["stack"]
    framework_note = ""
    if stack.get("framework") == "Microsoft Agent Framework":
        framework_note = """<p><strong>Why Microsoft Agent Framework?</strong> Its reusable agent and
          workflow abstractions provide a common way to connect models, tools, and specialist agents.
          This gives teams a clearer structure to inspect and adapt instead of rebuilding coordination
          from scratch. The demo&rsquo;s own code determines which capabilities are implemented.</p>
          <a class="text-link" href="../building-blocks.html#agent-framework">Explore the Framework building blocks &#8594;</a>"""
    return f"""<section class="page-hero wrap scenario-hero">
      <a class="back-link" href="../explore.html">&#8592; All scenarios</a>
      <p class="eyebrow">{text(story['industry'])} / {text(entry['title'])}</p>
      <h1>{text(story['headline'])}</h1><p class="lede">{text(story['summary'])}</p>
      <div class="meta-row"><span class="status">{text(entry['status'])}</span>
      <span>Technical level: {text(entry.get('difficulty', 'not specified'))}</span></div>
      <div class="actions"><a class="button primary" href="{quickstart}">Run this example &#8599;</a>
      <a class="button secondary" href="{code}">Explore the code &#8599;</a></div>
      <p class="hero-note">Setup instructions open on GitHub. This page does not run the application.</p>
    </section>
    <section class="wrap section problem-grid"><div><p class="eyebrow">The business need</p><h2>Why this matters</h2>
      <p class="lede small">{text(story['problem'])}</p></div>
      <div class="outcome-panel"><p class="eyebrow">What you can learn</p><p>{text(story['outcome'])}</p></div></section>
    <section class="wrap section"><p class="eyebrow">The workflow, at a glance</p><h2>How it comes together</h2>
      {workflow(story['steps'])}<p class="caption">A simplified view. The source documentation contains implementation details.</p></section>
    <section class="wrap section"><div class="reality-panel"><p class="eyebrow">Before you build</p>
      <h2>What&rsquo;s real. What&rsquo;s simulated.</h2><p>{text(story['reality'])}</p>
      <p><strong>Customer context:</strong> AgentVerse examples are based on real customer use cases
      being used or deployed in large enterprises. The public version illustrates that work;
      its sample data and simulation modes are not the customer&rsquo;s production environment.</p>
      <p>Use a test environment and non-sensitive data. Review identity, permissions, safety, evaluation,
      and operating costs before adapting this for a real business process.</p></div></section>
    <section class="wrap section detail-grid"><div><p class="eyebrow">Under the hood</p>
      <h2>The technical picture</h2><dl class="tech-list">
      <dt>Coordination pattern</dt><dd>{text(entry.get('orchestration', 'See source'))}</dd>
      <dt>Framework</dt><dd>{text(stack.get('framework', 'See source'))}</dd>
      <dt>Application</dt><dd>{text(stack.get('backend', ''))} / {text(stack.get('frontend', ''))}</dd>
      </dl>{framework_note}<div class="chips">{services}</div>
      <details><summary>Explore the agents and participants</summary><ul class="agent-list">{agents}</ul></details></div>
      <aside class="setup-panel"><p class="eyebrow">Make it your own</p><h2>Ready to try it?</h2>
      <ul class="check-list">{prerequisites}</ul>
      <p><strong>Costs:</strong> Browsing this site is free. Azure-backed examples can incur model,
      hosting, and other resource charges; check the setup guide and remove resources when finished.</p>
      <a class="button primary" href="{quickstart}">Open setup guide &#8599;</a>
      <a class="text-link" href="../get-started.html">New to AgentVerse? Start here &#8594;</a>
      <p>All examples can be co-built with Microsoft staff if needed.</p>
      <a class="text-link" href="../get-started.html#co-build">Discuss co-building this example &#8594;</a></aside></section>"""


def get_started() -> str:
    return f"""<section class="page-hero wrap"><p class="eyebrow">A practical first step</p>
      <h1>From an idea<br>to <em>something working.</em></h1>
      <p class="lede">You don&rsquo;t need an Azure subscription to explore.
      When you&rsquo;re ready to run an example, its own guide is the source of truth.</p>
      <a class="text-link" href="about.html#who-is-this-for">Find a starting point for your role &#8594;</a></section>
    <section class="wrap section"><div class="start-grid">
      <article class="setup-panel"><p class="eyebrow">I want to understand the possibilities</p><h2>Start with the story.</h2>
      <p>Explore a business problem, follow the workflow, and read what is real versus simulated.
      No installation or sign-in required to browse these pages.</p>
      <a class="text-link" href="explore.html">Find a relevant scenario &#8594;</a></article>
      <article class="setup-panel"><p class="eyebrow">I want to start building</p><h2>Start with the source.</h2>
      <p>Choose one example and follow its setup guide. Each application is independent:
      you don&rsquo;t need to deploy the entire collection.</p>
      <a class="text-link" href="scenarios/foundryairlines-demo.html">Explore the beginner-level airline example &#8594;</a></article>
    </div></section>
    <section class="wrap section" id="co-build" aria-labelledby="co-build-title">
      <div class="purpose-panel"><div><p class="eyebrow">You don&rsquo;t have to build alone</p>
      <h2 id="co-build-title">Co-build with Microsoft.</h2>
      <p class="lede small">All examples can be co-built with Microsoft staff if needed.</p></div>
      <div><p>These examples are based on real customer use cases being used or deployed in large
      enterprises. Your Microsoft team can work with you to explore how a scenario could fit your
      organization, rather than treating the public demo as a finished deployment.</p>
      <p>To start, share the scenario link with your Microsoft account team or technical contact.
      Describe the business outcome, the systems you want to connect, and your security and deployment
      requirements. Agree the scope, staff availability, and engagement arrangements together.</p>
      <p>You can also start independently with the source code and bring questions to that conversation.
      Co-building does not replace your organization&rsquo;s production review or operating responsibilities.</p></div></div>
    </section>
    <section class="wrap section reading-width"><p class="eyebrow">Your route to a first build</p><h2>Small steps. A useful starting point.</h2>
      <ol class="guide-steps">
      <li><h3>Choose a scenario and check its boundaries</h3><p>Read the business need, workflow, maturity status,
      and simulation notes. For a guided local replay with no Azure calls, consider
      <a href="scenarios/sre-agent-demo.html">Azure SRE Agent</a>. It still needs local application setup.</p></li>
      <li><h3>Prepare a safe environment</h3><p>Use a development machine or approved sandbox, Git, and the runtimes
      specified by the example. Azure-backed examples may also require an Azure subscription, CLI sign-in,
      permissions, model availability, and quota. Never put secrets in source control.</p></li>
      <li><h3>Run one example as documented</h3><p>Open its GitHub setup guide. Start with the supplied sample data
      and observe the full workflow before changing it. There is no universal deploy command for all scenarios.</p></li>
      <li><h3>Adapt and evaluate</h3><p>Change one thing at a time: a tool, an instruction, or a data source.
      Use the example&rsquo;s evaluations where provided, add your own test cases, and verify failure paths and human approvals.</p></li>
      <li><h3>Plan the next step responsibly</h3><p>Before real users or business data, review security, privacy,
      monitoring, cost controls, and ownership. Delete test resources you no longer need.</p></li></ol>
    </section>
    <section class="wrap section"><div class="reality-panel"><p class="eyebrow">Two different experiences</p>
      <h2>The public website is not the live demo portal.</h2>
      <p>This GitHub Pages site explains the scenarios and links to their code. It does not host agent backends,
      store credentials, or provision resources. The separate Azure portal can bring deployed demos together;
      access depends on the operator&rsquo;s deployment and authentication settings.</p>
      <a class="text-link" href="{source_link('infra/README.md')}">Read about deploying the shared platform &#8599;</a>
      </div></section>"""


def building_blocks(entries: list[dict]) -> str:
    framework_links = "".join(
        f'<li><a href="scenarios/{text(entry["name"])}.html">{text(entry["title"])} &#8594;</a></li>'
        for entry in entries if entry["stack"].get("framework") == "Microsoft Agent Framework"
    )
    blocks = [
        ("Coordination", "Give each participant a clear job.",
         "One agent can hand work to the next, or an orchestrator can coordinate specialists. The application controls how their outputs fit together.",
         lambda e: e.get("orchestration") in ("sequential", "orchestrator-workers")),
        ("Tools and grounding", "Connect answers to useful information.",
         "Tools let agents retrieve information or request actions. Grounding gives the model relevant context; it does not guarantee that every answer is correct.",
         lambda e: "tools" in e.get("capabilities", [])),
        ("Human review", "Keep people in consequential decisions.",
         "Pause for a person to review a proposed action. Approval should be enforced by the application, not just requested in the prompt.",
         lambda e: "human-in-the-loop" in e.get("capabilities", [])),
        ("Evaluation", "Check behavior, not just a convincing answer.",
         "Compare outputs against test cases and inspect trade-offs. Interactive model comparisons are useful exploration, not proof of production quality.",
         lambda e: "evals" in e.get("capabilities", [])),
        ("Governance and visibility", "Understand what happened and why.",
         "Track decisions and tool calls, limit access, and design for safe failure. Reference examples are starting points for your own security and operating model.",
         lambda e: "governance" in e.get("capabilities", [])),
    ]
    cards = ""
    for label, heading, description, matches in blocks:
        links = "".join(
            f'<li><a href="scenarios/{text(entry["name"])}.html">{text(entry["title"])} &#8594;</a></li>'
            for entry in entries if matches(entry)
        )
        cards += f'<article class="block-card"><p class="eyebrow">{label}</p><h2>{heading}</h2><p>{description}</p><ul>{links}</ul></article>'
    return f"""<section class="page-hero wrap"><p class="eyebrow">Ideas you can reuse</p>
      <h1>Different scenarios.<br><em>Shared building blocks.</em></h1>
      <p class="lede">You may not be building an airline or a factory application.
      The patterns behind them can still help you get started.</p></section>
      <section class="wrap section" id="agent-framework" aria-labelledby="framework-title">
      <div class="reality-panel"><p class="eyebrow">The foundation behind the Framework-based demos</p>
      <h2 id="framework-title">Why Microsoft Agent Framework?</h2>
      <p>Microsoft Agent Framework provides building blocks for agents and multi-agent workflows:
      connections to model providers, tool integration, state management, and explicit execution paths.
      Instead of assembling each integration from scratch, teams can use a shared programming model
      and focus on the business logic that makes their scenario useful.</p>
      <div class="journey-grid"><div><h3>Connect the pieces</h3>
      <p>Bring models, instructions, and tools together through reusable abstractions.</p></div>
      <div><h3>Make coordination explicit</h3>
      <p>Structure how agents and functions pass work and data through a multi-step process.</p></div>
      <div><h3>Adapt with less rework</h3>
      <p>Reuse components and integration patterns as you change tools, models, or the business workflow.</p></div></div>
      <p>These are Framework capabilities, not a claim that every demo uses every feature. Application-level
      authorization, approvals, evaluation, and production readiness still need to be designed and verified.</p>
      <p><strong>Framework-based examples in this collection:</strong></p><ul>{framework_links}</ul>
      <p>Model Evaluator uses direct inference and model discovery; the Azure SRE Agent example is a guided
      replay of a separate service. Neither is presented here as a Microsoft Agent Framework implementation.</p>
      <a class="text-link" href="https://learn.microsoft.com/agent-framework/overview/">Read the Microsoft Agent Framework overview &#8599;</a>
      </div></section>
      <section class="wrap section block-grid" aria-label="Agent building blocks">{cards}</section>"""


def build(output: Path) -> None:
    entries = load_catalog()
    stories = load_stories(entries)
    pages = {
        "index.html": page("Start building with AI agents", "Practical AI agent examples from Microsoft. Discover a scenario, understand the workflow, and build on the code.", home(entries, stories)),
        "explore.html": page("Explore scenarios", "Find an AI agent example by business need, industry, or technical level.", explore(entries, stories), "explore"),
        "building-blocks.html": page("Building blocks", "Understand the reusable patterns behind practical AI agents.", building_blocks(entries), "blocks"),
        "get-started.html": page("Get started", "Choose, run, and adapt your first AgentVerse example.", get_started(), "start"),
        "about.html": page("About AgentVerse", "Who AgentVerse is for, why it was developed, and how it helps turn agentic ideas into practical starting points.", about(), "about"),
    }
    for entry in entries:
        story = stories[entry["name"]]
        pages[f'scenarios/{entry["name"]}.html'] = page(
            entry["title"], story["summary"], scenario(entry, story), "explore", depth=1
        )
    for relative, content in pages.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {len(pages)} pages from {len(entries)} validated scenarios in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "_site")
    build(parser.parse_args().output.resolve())
