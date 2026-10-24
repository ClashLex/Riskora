# Build the React frontend.
FROM node:24-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Run the Python API and serve the built frontend from the same origin.
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    RISKORA_DB=/tmp/riskora/riskora.sqlite3 \
    RISKORA_UPLOAD_DIR=/tmp/riskora/uploads \
    RISKORA_AUTO_LOAD_SYNTHETIC=true
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/app/ /app/backend/app/
COPY --from=frontend-build /build/frontend/dist/ /app/frontend/dist/
RUN mkdir -p /tmp/riskora
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
