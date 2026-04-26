# Frontend container — Vite SPA built and served by nginx.
#
# Vite reads VITE_* env vars at BUILD time. Production values live in
# the committed .env file (Cloud Run public URLs + Supabase anon key —
# all public-safe). The build copies them into the static bundle, so we
# don't need build-args here.

FROM node:20-slim AS build
WORKDIR /app

# Cache dependency install when only sources change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Runtime: tiny nginx serving the built SPA ───────────
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# Cloud Run injects PORT=8080 by default; nginx config listens on 8080.
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
