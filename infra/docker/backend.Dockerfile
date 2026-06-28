FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    FINEVENT_WORKSPACE_ROOT=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY alembic.ini ./
COPY configs ./configs
COPY infra ./infra
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[api,db,ingestion,vietnamese,rag,workflow,llm,evaluation]"

COPY infra/docker/backend-entrypoint.sh /usr/local/bin/finevent-backend-entrypoint
RUN chmod +x /usr/local/bin/finevent-backend-entrypoint

EXPOSE 8000

ENTRYPOINT ["finevent-backend-entrypoint"]
CMD ["python", "-m", "uvicorn", "finevent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
