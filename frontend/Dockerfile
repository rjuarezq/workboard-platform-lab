# ==========================================
# STAGE 1: (Builder) Install locked dependencies and compile the React/Vite SPA
# ==========================================

FROM ghcr.io/pnpm/pnpm:11.5.3 AS builder

RUN pnpm runtime set node 24.16.0 -g

WORKDIR /app

COPY frontend/package.json frontend/pnpm-lock.yaml ./

RUN --mount=type=cache,id=workboard-pnpm-store,target=/pnpm/store,sharing=locked \
    pnpm install --frozen-lockfile

COPY frontend/ ./

RUN pnpm run build

# =====================================================================
# STAGE 2: (RUNTIME) Serve the React/Vite SPA with hardened Nginx OSS
# =====================================================================
FROM nginx:1.31.6-alpine3.24 AS runtime

COPY --from=builder /app/dist/ /usr/share/nginx/html
COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf

RUN rm -f /etc/nginx/conf.d/default.conf  \
    && chmod -R a=rX /usr/share/nginx/html \
    && chmod 444 /etc/nginx/nginx.conf

EXPOSE 8080

USER 101:101