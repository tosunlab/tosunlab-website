FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY app ./app
COPY content ./content
RUN useradd --system --uid 1000 web
USER web
EXPOSE 8080
CMD ["/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:create_app()"]
