FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN corepack enable && pnpm install --frozen-lockfile=false

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && node --test tests/api-auth.test.cjs && pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8080
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 8080
CMD ["node","server.js"]
