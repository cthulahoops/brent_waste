# Brent Waste Collection Calendar

A web scraper that extracts waste collection dates from the Brent Council website and generates an iCal calendar file.

## Usage

Set the `BRENT_PROPERTY_ID` environment variable to your property ID and run:

```bash
python waste_collection_scraper.py -o calendar.ics
```

## Deployment

Deployed on disco with:
- Web service serving the calendar file
- Cron job updating the calendar at 6am and 6pm Mon-Wed
- Shared volume for real-time updates

### Deploy Commands

```bash
# Add the project with GitHub repo and domain
disco projects:add --name YOUR_PROJECT_NAME --github YOUR_GITHUB_USER/YOUR_REPO --domain YOUR_DOMAIN

# Set the property ID environment variable
disco env:set --project=YOUR_PROJECT_NAME BRENT_PROPERTY_ID=YOUR_PROPERTY_ID
```

The calendar is available at `/calendar.ics` when deployed.
