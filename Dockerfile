FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.7.11 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY app ./app
RUN useradd --create-home --uid 1000 appuser
USER appuser
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]