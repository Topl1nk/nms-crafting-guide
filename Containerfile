# NMSii without installing Python: the TUI, and the static site.
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
# The site export and its markdown renderer, which `nms mcp` renders its
# markdown guide pages with. (site-data copies the rest of scripts/.)
COPY scripts/build_web.py scripts/build_markdown.py ./scripts/
RUN uv sync --frozen --no-dev

# The TUI. The inventory lives in XDG state, kept in a volume; saved portal
# addresses are data/locations.json, which compose mounts from the checkout.
# `nms mcp` in the same image is the MCP server (compose run -T, no tty).
FROM app AS tui
VOLUME /state
CMD ["nms"]

# The same two steps the Pages workflow runs -- the Python export into web/,
# then the Svelte build around it into dist/ -- and a plain file server.
# All of scripts/, as the export may call on its neighbours.
FROM app AS site-data
COPY scripts ./scripts
COPY web ./web
COPY docs ./docs
RUN python scripts/build_web.py

# The node major here follows `node` in mise.toml's [tools].
FROM docker.io/library/node:24-slim AS site-build
WORKDIR /site
# Packages first, so editing a component does not re-download them.
COPY package.json package-lock.json ./
RUN npm ci
COPY vite.config.js ./
COPY site ./site
COPY --from=site-data /app/web ./web
RUN npm run build

FROM docker.io/library/python:3.13-slim AS site
COPY --from=site-build /site/dist /srv
EXPOSE 8001
CMD ["python", "-m", "http.server", "8001", "--directory", "/srv"]
