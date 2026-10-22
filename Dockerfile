# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false
# Poetry in its own venv (Poetry docs, "Installing manually"); app dependencies go to the image's Python.
RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install --no-cache-dir poetry==2.5.1 \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Tests, lint and type checks: the source is mounted at /app by compose.
FROM base AS dev
RUN poetry install --no-root --with dev
COPY . .

FROM base AS runtime
RUN poetry install --no-root --only main
COPY payment_gateway_api ./payment_gateway_api
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["uvicorn", "--factory", "payment_gateway_api.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
