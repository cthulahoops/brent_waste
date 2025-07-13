FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /site

COPY pyproject.toml uv.lock /site/

RUN uv sync --frozen

COPY . /site
COPY start.sh /start.sh

RUN mkdir -p dist

RUN chmod +x /start.sh

CMD ["/start.sh"]
