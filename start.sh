#!/bin/sh

# Create dist directory if it doesn't exist
mkdir -p /site/dist

# Generate waste calendar if it doesn't exist
if [ ! -f "/site/dist/$WASTE_CALENDAR_FILENAME" ]; then
    echo "No waste calendar found, generating..."
    uv run python waste_collection_scraper.py -o /site/dist/$WASTE_CALENDAR_FILENAME
fi

# Generate LNHS calendar if it doesn't exist
if [ ! -f "/site/dist/$LNHS_CALENDAR_FILENAME" ]; then
    echo "No LNHS calendar found, generating..."
    uv run python lnhs_calendar_scraper.py -o /site/dist/$LNHS_CALENDAR_FILENAME
fi

# Start web server
python -m http.server 8080 -d /site/dist
