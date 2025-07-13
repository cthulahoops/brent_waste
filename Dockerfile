FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /site

COPY pyproject.toml uv.lock /site/

RUN uv sync --frozen

COPY . /site

RUN --mount=type=secret,id=property_id \
    BRENT_PROPERTY_ID=$(cat /run/secrets/property_id) \
    uv run python waste_collection_scraper.py -o dist/calendar.ics
