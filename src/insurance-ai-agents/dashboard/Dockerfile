# Insurance dashboard — the demo's web tile. Builds the Vite SPA and serves it
# with nginx on :8080. The SPA calls /api and /ws relative to its own origin,
# and nginx proxies those to the backend container over the shared Container
# Apps environment's internal DNS (see 05-agentverse-backend.envsh).
#
# Build context is this folder (src/insurance-ai-agents/dashboard).
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Empty API base => the app uses same-origin /api and /ws, which nginx proxies.
ENV VITE_API_URL=""
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY 05-agentverse-backend.envsh /docker-entrypoint.d/05-agentverse-backend.envsh
RUN chmod +x /docker-entrypoint.d/05-agentverse-backend.envsh
EXPOSE 8080
