# syntax=docker/dockerfile:1

FROM node:22-bookworm AS vendor
WORKDIR /opt
RUN git clone --depth 1 --branch v0.4.7 https://github.com/colanode/colanode.git colanode \
  && cd colanode \
  && npm install --ignore-scripts --engine-strict=false

FROM python:3.12-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COLANODE_DATA_DIR=/data \
    COLANODE_ASSETS_DIR=/opt/colanode/assets \
    SIDECAR_HOST=127.0.0.1 \
    SIDECAR_PORT=3921 \
    SIDECAR_URL=http://127.0.0.1:3921 \
    SIDECAR_AUTO_START=true \
    BRIDGE_HOST=0.0.0.0 \
    BRIDGE_PORT=8786 \
    MCP_DNS_REBINDING_PROTECTION=false

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=vendor /opt/colanode /app/vendor/colanode
COPY pyproject.toml README.md ./
COPY src ./src
COPY sidecar ./sidecar

RUN pip install --no-cache-dir -e . \
  && cd /app/sidecar && npm install --engine-strict=false \
  && mkdir -p /data

VOLUME ["/data"]
EXPOSE 8786

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8786/ | grep -q sci-colanode-api || exit 1

CMD ["python", "-m", "sci_colanode_api.main"]
