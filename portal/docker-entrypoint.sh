#!/bin/sh
# Turn the DEMOS_JSON env var into a browser-readable config.js. The nginx
# base image runs every /docker-entrypoint.d/*.sh script before starting nginx.
#
# DEMOS_JSON is a JSON object of demo_id => public web URL, e.g.
#   {"foundryairlines-demo":"https://...","insurance-ai-agents":"https://..."}
set -e

TARGET=/usr/share/nginx/html/config.js

# Note: do NOT use ${DEMOS_JSON:-{}} — in POSIX sh the first '}' closes the
# parameter expansion, leaving a stray '}' literal and producing invalid JS.
DEMOS="$DEMOS_JSON"
if [ -z "$DEMOS" ]; then
  DEMOS="{}"
fi

printf 'window.__DEMOS__ = %s;\n' "$DEMOS" > "$TARGET"
echo "agentverse: wrote runtime demo config to $TARGET"
