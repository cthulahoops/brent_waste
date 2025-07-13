FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /site

COPY pyproject.toml uv.lock /site/

RUN uv sync --frozen

COPY . /site

RUN mkdir -p dist

RUN chmod +x /site/start.sh

CMD ["/site/start.sh"]
