# Verified Company Profile System — Web (Next.js)
# Multi-stage build for Node.js 20 with pnpm

# === Dependencies stage ===
FROM node:20-alpine AS deps

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy workspace config and web package
COPY pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
COPY packages/ packages/

RUN cd apps/web && pnpm install --frozen-lockfile || pnpm install

# === Builder stage ===
FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY apps/web/ apps/web/
COPY pnpm-workspace.yaml ./

WORKDIR /app/apps/web
RUN pnpm build

# === Runtime stage ===
FROM node:20-alpine AS runtime

# Security: run as non-root
RUN addgroup --system --gid 1001 vcps && \
    adduser --system --uid 1001 vcps

WORKDIR /app

# Copy standalone output
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./.next/static
COPY --from=builder /app/apps/web/public ./public

USER vcps

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
EXPOSE 3000

CMD ["node", "server.js"]
