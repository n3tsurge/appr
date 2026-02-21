# =============================================================================
# Stage 1: base — Node.js foundation
# =============================================================================
FROM node:20-alpine AS base

ENV NODE_ENV=development

WORKDIR /app

# =============================================================================
# Stage 2: development — install all deps, expose Vite dev server port
# =============================================================================
FROM base AS development

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# =============================================================================
# Stage 3: builder — compile production assets
# =============================================================================
FROM base AS builder

ENV NODE_ENV=production

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# =============================================================================
# Stage 4: production — serve compiled assets with nginx as non-root user
# =============================================================================
FROM nginx:1.25-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user and fix permissions
RUN addgroup -g 1001 appuser && \
    adduser -u 1001 -G appuser -H -D appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

USER appuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
