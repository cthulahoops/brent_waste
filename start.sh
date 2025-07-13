#!/bin/bash

# Generate initial calendar
BRENT_PROPERTY_ID=$BRENT_PROPERTY_ID uv run python waste_collection_scraper.py -o /site/dist/calendar.ics

# Start HTTP server
python -m http.server 8080 -d /site/dist
