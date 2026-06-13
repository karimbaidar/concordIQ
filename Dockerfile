FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY backend/ backend/
RUN python -m pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --extra foundry-hosting

COPY data/ data/
COPY ontology/ ontology/
COPY artifacts/replay/sanitized/ artifacts/replay/sanitized/

CMD ["/app/.venv/bin/python", "-m", "concord.ms_agent.foundry_hosted_entrypoint"]
