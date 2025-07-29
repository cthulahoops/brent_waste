#!/bin/sh

# Create dist directory if it doesn't exist
mkdir -p /site/dist

cp /site/index.html /site/dist/index.html

# Generate waste calendar if it doesn't exist
if [ ! -f "$WASTE_CALENDAR_FILENAME" ]; then
    echo "No waste calendar found, generating..."
    uv run python waste_collection_scraper.py
fi

# Generate LNHS calendar if it doesn't exist
if [ ! -f "$LNHS_CALENDAR_FILENAME" ]; then
    echo "No LNHS calendar found, generating..."
    uv run python lnhs_calendar_scraper.py --no-cache
fi

# Start web server
python -m http.server 8080 -d /site/dist
