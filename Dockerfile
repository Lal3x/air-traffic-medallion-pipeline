FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

COPY pyproject.toml poetry.lock* ./
COPY src ./src
COPY config ./config
COPY README.md ./README.md

RUN poetry install --only main --no-interaction --no-root

RUN mkdir -p /app/data/bronze /app/data/silver /app/data/gold /app/data/rejected /app/data/observability

EXPOSE 8501

USER nobody

CMD ["poetry", "run", "streamlit", "run", "src/air_traffic_beam/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
