# AgentVerse portal — static, catalog-driven SPA served by nginx on :8080.
# The catalog.json is baked in at build time; demo iframe URLs are injected at
# container start from the DEMOS_JSON env var (see docker-entrypoint.sh).
FROM nginx:1.27-alpine

# Static assets (index.html, app.js, styles.css, catalog.json).
COPY public/ /usr/share/nginx/html/

# nginx listens on 8080 (non-root friendly) and never caches config.js.
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY docker-entrypoint.sh /docker-entrypoint.d/99-agentverse-config.sh
# Normalize CRLF -> LF (files may be authored on Windows) and make executable,
# otherwise the shebang becomes "#!/bin/sh\r" and the script fails with "not found".
RUN sed -i 's/\r$//' /docker-entrypoint.d/99-agentverse-config.sh \
    && chmod +x /docker-entrypoint.d/99-agentverse-config.sh

EXPOSE 8080
