# ThermalWatch Frontend Multi-Stage Dockerfile
# Stage 1: Build static web bundle using Node 20
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies efficiently
COPY package*.json ./
RUN npm ci

# Copy frontend application source
COPY . .

# Inject build-time API base URL configuration (defaults to http://localhost:8000 for browser client)
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build production bundle
RUN npm run build

# Stage 2: Serve compiled static assets via lightweight Nginx Alpine server
FROM nginx:alpine AS runner

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration supporting React SPA routing on port 5173
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:5173/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
