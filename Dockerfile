FROM ghcr.io/astral-sh/uv:python3.12-alpine

ARG BRENT_PROPERTY_ID=""

WORKDIR /site

COPY pyproject.toml uv.lock /site/

RUN uv sync --frozen

COPY . /site

RUN --mount=type=secret,id=property_id,env=BRENT_PROPERTY_ID \
    uv run python waste_collection_scraper.py -o dist/calendar.ics
