# Playwright runner with browsers preinstalled, plus the Docker CLI so the
# SSE resilience test can restart the sibling `app` container via the host
# Docker socket (mounted in docker-compose.test.yml) — PLAN.md §12.
FROM mcr.microsoft.com/playwright:v1.49.1-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /test

COPY package.json ./
RUN npm install

COPY . .

CMD ["npx", "playwright", "test"]
