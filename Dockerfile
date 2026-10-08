# syntax=docker/dockerfile:1

FROM alpine/git:latest AS vendor
WORKDIR /src
RUN git clone --depth 1 --branch v0.4.7 --filter=blob:none --sparse https://github.com/colanode/colanode.git colanode \
  && cd colanode \
  && git sparse-checkout set packages/client packages/core packages/crdt assets

FROM python:3.12-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COLANODE_DATA_DIR=/data \
    COLANODE_ASSETS_DIR=/app/vendor/colanode/assets \
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

COPY --from=vendor /src/colanode/packages/client /app/vendor/colanode/packages/client
COPY --from=vendor /src/colanode/packages/core /app/vendor/colanode/packages/core
COPY --from=vendor /src/colanode/packages/crdt /app/vendor/colanode/packages/crdt
COPY --from=vendor /src/colanode/assets /app/vendor/colanode/assets

COPY sidecar/package.json sidecar/package-lock.json sidecar/.npmrc ./sidecar/
RUN cd /app/sidecar \
  && npm ci --engine-strict=false --no-audit --no-fund \
  && ln -s /app/sidecar/node_modules /app/vendor/colanode/node_modules

COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install --no-cache-dir -e . && mkdir -p /data

COPY sidecar ./sidecar

VOLUME ["/data"]
EXPOSE 8786

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8786/ | grep -q sci-colanode-api || exit 1

CMD ["python", "-m", "sci_colanode_api.main"]
