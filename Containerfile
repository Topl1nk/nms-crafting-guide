# NMS Items without installing Python: the TUI, and the static site.
#
#   podman compose run --rm tui     the terminal app
#   podman compose up site          the web version on http://localhost:8001
#
# compose.yaml picks the stage; `docker compose` reads the same files.

FROM docker.io/library/python:3.13-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/app/.venv/bin:$PATH \
    NMS_ITEMS_DATA=/app/data \
    XDG_STATE_HOME=/state
WORKDIR /app
# Dependencies first, so editing the code does not re-download Textual.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY data ./data
RUN uv sync --frozen --no-dev

# The TUI. The inventory lives in XDG state, kept in a volume; saved portal
# addresses are data/locations.json, which compose mounts from the checkout.
FROM app AS tui
VOLUME /state
CMD ["nms"]

# The same export the Pages workflow runs, then a plain file server.
FROM app AS site-build
COPY scripts/build_web.py ./scripts/
COPY web ./web
COPY docs ./docs
RUN python scripts/build_web.py

FROM docker.io/library/python:3.13-slim AS site
COPY --from=site-build /app/web /srv
EXPOSE 8001
CMD ["python", "-m", "http.server", "8001", "--directory", "/srv"]
