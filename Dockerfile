# syntax=docker/dockerfile:1.7
#
# Multi-stage build for CrumbBob.
#
# Stage 1 (builder): install build deps + compile wheel.
# Stage 2 (runtime): copy wheel into a slim image, drop privileges, run.
#
# Image size on linux/amd64 with the [web] extra: ~110 MB.

# ---------------------------------------------------------------------------
# Build stage
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

# Build-time deps for any optional C extensions (tiktoken, watchdog).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY crumdbob ./crumdbob
COPY web ./web
COPY examples ./examples

# Build the wheel — pip-only, no setuptools.develop / editable install.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip build && python -m build --wheel --outdir /dist

# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# OCI labels for registry metadata.
LABEL org.opencontainers.image.title="CrumbBob" \
      org.opencontainers.image.description="Replayable software memory for IBM Bob development sessions" \
      org.opencontainers.image.source="https://github.com/XioAISolutions/Crumb-Bob" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="XIO AI Solutions"

# Create a non-root user. UID 10001 is well above the system-user range
# and high enough to avoid colliding with host users mounting volumes.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin crumdbob

# Install the wheel + runtime extras. We do this as root so site-packages
# is read-only to the runtime user — defense in depth against arbitrary
# pip-install from a compromised container.
COPY --from=builder /dist/*.whl /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    whl="$(find /tmp -maxdepth 1 -name '*.whl' -print -quit)" \
    && pip install "${whl}[web,watch,ui]" \
    && rm /tmp/*.whl

# Default data location is a writable volume mount point.
ENV CRUMDBOB_DATA_DIR=/data \
    CRUMDBOB_LOG_FORMAT=json \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p "${CRUMDBOB_DATA_DIR}" && chown -R crumdbob:crumdbob "${CRUMDBOB_DATA_DIR}"
VOLUME ["${CRUMDBOB_DATA_DIR}"]

USER crumdbob
WORKDIR /home/crumdbob

EXPOSE 8000

# Container-side healthcheck. Orchestrators (Docker swarm, ECS) consume
# this to drive deployment rollouts. Kubernetes prefers a probe defined
# in the Pod spec — but having one here makes `docker run` healthy too.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        r=urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3); \
        sys.exit(0 if r.status==200 else 1)" || exit 1

# `serve` binds to 0.0.0.0 so traffic from the container's interface reaches
# uvicorn; tighten via the CRUMDBOB_API_KEY env in your orchestrator's secret
# manager when exposing beyond localhost.
ENTRYPOINT ["crumdbob"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
