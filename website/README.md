# AgentVerse public website

A static, public-facing introduction to AgentVerse for GitHub Pages. This is
separate from the Azure-hosted demo portal in `portal/`: it explains scenarios
and links to source and setup guides, but does not execute agents or provision
Azure resources.

The first draft includes a homepage, a dedicated **About AgentVerse** page in
the main navigation explaining its audience and purpose, a searchable scenario collection, one page
per scenario, reusable building blocks, and a getting-started guide. The homepage
workflow slider includes every scenario, with previous/next buttons, direct
selection dots, and keyboard arrow navigation. It does not auto-advance; without
JavaScript, the same slides remain horizontally scrollable. All pages
are pre-rendered and readable without JavaScript. Search, shareable filters, and
light/dark theme selection progressively enhance the experience. There are no
CDN dependencies, trackers, credentials, backend services, or external fonts.

## Preview locally

From the repository root:

```powershell
python -m pip install -r website\requirements.txt
python website\build.py
python -m unittest discover -s website -p "test_*.py"
python -m http.server 8098 --bind 127.0.0.1 --directory website\_site
```

Open `http://127.0.0.1:8098/`. Stop the server with Ctrl+C. Generated output is
ignored by Git. Each generated page includes its CSS and JavaScript, so it can
also be opened directly from disk (linked pages must stay together).

### Optional browser checks

With the preview server running:

```powershell
python -m pip install -r website\requirements-browser.txt
python -m playwright install chromium
python website\browser_smoke.py
```

Alternatively use `--channel msedge` with an existing Microsoft Edge installation.
The checks exercise filters, reset, theme switching, navigation, no-JavaScript
content, and all pages at mobile, tablet, and desktop widths. Pass
`--screenshot-dir <local-folder>` to capture previews. These optional checks
are separate from the dependency-light publication checks.

## Publish to GitHub Pages

1. A repository administrator enables **Settings > Pages > Build and
   deployment > Source: GitHub Actions**. Organization policy must permit
   Pages for this repository.
2. Merge the website and `.github/workflows/pages.yml` into `main`.
3. The **Public website** workflow checks and builds the site, then deploys
   through the `github-pages` environment. Approve any configured environment
   protection rules. It can also be run manually from `main`.
4. Use the deployment URL returned by the workflow. With default public Pages
   configuration, the expected URL is `https://azure.github.io/AgentVerse/`.

Pull requests build and check the artifact but **never publish**. Branch
dispatches also do not deploy. Publication requires repository permissions;
the presence of this workflow alone does not mean the site is live.
All internal URLs are relative and support the `/AgentVerse/` project prefix.
GitHub source links intentionally point to `main`, where the published site
and its source should match.

## Content contract

- `src/*/agentverse.yaml`: source of truth for identity, maturity, difficulty,
  technical stack, agents, and capabilities. The builder reuses the existing
  manifest validator directly; it does not edit the portal or generated catalog.
- `scenarios.json`: reviewed, plain-language context keyed by the same demo ID.
  Each entry has `industry`, `headline`, `summary`, `problem`, `outcome`,
  `steps`, `reality`, `prerequisites`, and a repo-relative `start_path`.
  Keep limitations and prerequisites grounded in the example's README.
- `build.py`: static page composition and fail-fast content checks.
- `styles.css` / `site.js`: shared presentation and progressive enhancement,
  inlined into each generated HTML page.
- `test_build.py`: catalog coverage, basic accessibility structure, escaping,
  local links, source paths, project-subpath support, and invalid-input checks.

When adding a demo, add its public explanation to `scenarios.json` as well.
Missing copy or broken quickstart paths fail the build rather than silently
publishing incomplete scenario pages. Building-block links derive from manifest
capabilities. The homepage has a small editorial selection, not a second catalog.

Do not add deployment URLs automatically from private operator configuration.
Only link a live demo after its owner confirms it is intended for public access.
Never describe experimental examples or replay modes as production-ready.
