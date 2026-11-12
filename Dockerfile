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

# Crear usuario sin privilegios para Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-builder /app/frontend/dist ./dist

# Crear directorios necesarios y asignar permisos al usuario 1000
RUN mkdir -p /app/data /data /app/uploads/avatars /app/uploads/questions \
    && chown -R user:user /app /data \
    && chmod -R 775 /app /data

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860 \
    DATABASE_URL=sqlite:////data/peak.db \
    PYTHONPATH=/app

EXPOSE 7860

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
