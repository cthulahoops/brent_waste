#!/bin/bash

uv run python waste_collection_scraper.py -o /site/dist/calendar.ics
python -m http.server 8080 -d /site/dist
