# AgentVerse Portal

A lightweight, **catalog-driven** single-page app that shows every AgentVerse
demo in one place — **one tab per demo**, each embedding the demo's deployed
frontend in an iframe. Served by nginx on port **8080** and deployed as an Azure
Container App by the global Terraform in [`../infra/`](../infra/).

## How it works

```
catalog.json  (metadata, baked in at build)  ─┐
                                               ├─►  app.js renders one tab per demo
config.js     (demo_id → URL, injected at run) ┘
```

- **`public/catalog.json`** — generated from every demo's `agentverse.yaml` by
  `src/templates/catalog/build_catalog.py`. Baked into the image at build time.
  Copy it in before building: `Copy-Item ../src/catalog.json public/catalog.json`.
- **`config.js`** — written at container start by `docker-entrypoint.sh` from
  the `DEMOS_JSON` env var (`{demo_id: "https://…"}`), which Terraform sets to
  each demo's deployed web URL. Locally it defaults to an empty map.
- The two are linked by `demo_id` (catalog `name` === `DEMOS_JSON` key). A demo
  with metadata but no URL renders a “Not deployed” tab; a deployed demo with no
  metadata still gets a minimal tab.

Each tab shows the demo's title, tagline, agents and tags, an **Open in new
tab** button, and the iframe. If the iframe does not load within a few seconds
(embedding blocked by `X-Frame-Options`/CSP, or a sign-in flow), a fallback
prompts the user to open the demo directly.

## Run it locally

```powershell
# 1. Bake the catalog
python ../src/templates/catalog/build_catalog.py --write
Copy-Item ../src/catalog.json public/catalog.json -Force

# 2. (optional) point some tabs at real/placeholder URLs
'window.__DEMOS__ = {"foundryairlines-demo":"https://example.org/"};' | Set-Content public/config.js

# 3. Serve
cd public
python -m http.server 8099
# open http://localhost:8099
```

## Build the image

```bash
docker build -t <acr>.azurecr.io/portal:latest .
```

The global Terraform builds this image with `az acr build` (no local Docker
needed) and injects `DEMOS_JSON` — you normally don't build it by hand.

## Files

```
portal/
├── Dockerfile              # nginx:alpine serving public/ on :8080
├── nginx.conf              # SPA fallback + no-cache for config.js/catalog.json
├── docker-entrypoint.sh    # writes config.js from DEMOS_JSON at start-up
└── public/
    ├── index.html
    ├── app.js              # merges catalog.json + config.js, renders tabs
    ├── styles.css
    ├── config.js           # local fallback (overwritten in the container)
    └── catalog.json        # generated; baked in at build
```
