# Stage 1: Build React Frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend

RUN npm install -g pnpm
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY frontend/ ./
RUN pnpm run build

# Stage 2: Python Backend with Embedded Frontend
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-builder /app/frontend/dist ./dist

# Create necessary directories
RUN mkdir -p uploads/avatars uploads/questions /data

ENV PORT=8080
ENV DATABASE_URL=sqlite:////data/peak.db
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
