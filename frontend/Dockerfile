# frontend/Dockerfile
# Multi-stage build: compile the Vite app, then serve the static bundle with nginx.

# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Injected at build time so the built bundle points at the right API.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# --- Runtime stage ---
FROM nginx:alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx:alpine ships an unprivileged "nginx" user; run as non-root and let it
# own the dirs/files it needs to write pid/cache/logs. The base image's
# nginx.conf sets `pid /run/nginx.pid;` (root-owned, unwritable by "nginx"),
# so repoint it at a world-writable path.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx \
    && sed -i 's#pid\s*/run/nginx.pid;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf

USER nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
