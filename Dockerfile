# syntax=docker/dockerfile:1

# ---- Stage 1: build the Next.js static export (PLAN.md §11) ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend, serving the static export on one port ----
FROM python:3.12-slim AS backend
WORKDIR /app

RUN pip install --no-cache-dir uv

# Needs the full backend/ tree (not just the lockfile) before `uv sync`,
# since finally-backend is installed from local source (hatchling build).
COPY backend/ ./
RUN uv sync --frozen --no-dev

COPY --from=frontend-build /frontend/out ./static

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
