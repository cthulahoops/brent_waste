FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /site

COPY pyproject.toml uv.lock /site/

RUN uv sync --frozen

COPY . /site

RUN --mount=type=secret,id=BRENT_PROPERTY_ID BRENT_PROPERTY_ID=$(cat /run/secrets/BRENT_PROPERTY_ID) uv run python waste_collection_scraper.py -o dist/calendar.ics
