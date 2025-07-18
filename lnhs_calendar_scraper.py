#!/usr/bin/env python3
"""
Script to extract events from LNHS calendar website and generate consolidated iCal file.
Scrapes calendar grid pages to extract event IDs, downloads individual iCal files,
and merges them into a single calendar.
"""

import argparse
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event


class LNHSCalendarScraper:
    """
    Scraper for LNHS calendar events.
    """

    def __init__(self, cache_dir="cache", base_url="https://www.lnhs.org.uk"):
        self.cache_dir = Path(cache_dir)
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; LNHS Calendar Scraper)"}
        )

        # Ensure cache directory exists
        self.cache_dir.mkdir(exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def get_calendar_page(self, year, month, use_cache=True):
        """
        Download or retrieve cached calendar page for given year/month.
        """
        cache_file = self.cache_dir / f"calendar_{year}_{month:02d}.html"

        if use_cache and cache_file.exists():
            # Check if cache is less than 1 hour old
            if time.time() - cache_file.stat().st_mtime < 3600:
                self.logger.info(f"Using cached calendar for {year}/{month:02d}")
                return cache_file.read_text(encoding="utf-8")

        # Download calendar page
        url = f"{self.base_url}/index.php/activities/full-programme/monthcalendar/{year}/{month}/-"
        self.logger.info(f"Downloading calendar page: {url}")

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Cache the response
            cache_file.write_text(response.text, encoding="utf-8")

            return response.text

        except requests.RequestException as e:
            self.logger.error(f"Failed to download calendar page: {e}")
            return None

    def extract_event_ids(self, html_content):
        """
        Extract event IDs from calendar HTML content.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        event_ids = []

        # Look for event detail links
        pattern = r"/eventdetail/(\d+)/"
        links = soup.find_all("a", href=re.compile(pattern))

        for link in links:
            match = re.search(pattern, link.get("href"))
            if match:
                event_id = int(match.group(1))
                if event_id not in event_ids:
                    event_ids.append(event_id)

        self.logger.info(f"Found {len(event_ids)} unique event IDs")
        return sorted(event_ids)

    def download_event_ical(self, event_id, use_cache=True):
        """
        Download individual event iCal file.
        """
        cache_file = self.cache_dir / f"event_{event_id}.ics"

        if use_cache and cache_file.exists():
            self.logger.debug(f"Using cached iCal for event {event_id}")
            return cache_file.read_text(encoding="utf-8")

        # Download iCal file
        url = f"{self.base_url}/index.php/activities/full-programme/icals.icalevent/-?tmpl=component&evid={event_id}"
        self.logger.info(f"Downloading iCal for event {event_id}")

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Cache the response
            cache_file.write_text(response.text, encoding="utf-8")

            return response.text

        except requests.RequestException as e:
            self.logger.warning(f"Failed to download iCal for event {event_id}: {e}")
            return None

    def merge_ical_files(self, ical_contents):
        """
        Merge multiple iCal files into a single calendar.
        """
        master_calendar = Calendar()
        master_calendar.add("prodid", "-//LNHS Calendar Scraper//EN")
        master_calendar.add("version", "2.0")
        master_calendar.add("calscale", "GREGORIAN")
        master_calendar.add("method", "PUBLISH")

        events_added = 0

        for ical_content in ical_contents:
            if not ical_content:
                continue

            try:
                calendar = Calendar.from_ical(ical_content)

                # Extract events from the calendar
                for component in calendar.walk():
                    if component.name == "VEVENT":
                        master_calendar.add_component(component)
                        events_added += 1

            except Exception as e:
                self.logger.error(f"Failed to parse iCal content: {e}")
                continue

        self.logger.info(f"Merged {events_added} events into master calendar")
        return master_calendar

    def scrape_calendar(
        self, year, month_range=2, output_file="lnhs_events.ics", use_cache=True
    ):
        """
        Main scraping function to extract events and generate merged iCal.
        """
        current_date = datetime.now()
        start_year = year or current_date.year
        start_month = current_date.month

        all_event_ids = []

        # Scrape calendar pages for specified months
        for month_offset in range(month_range):
            target_date = datetime(start_year, start_month, 1) + timedelta(
                days=32 * month_offset
            )
            target_year = target_date.year
            target_month = target_date.month

            self.logger.info(f"Scraping calendar for {target_year}/{target_month:02d}")

            # Get calendar page
            html_content = self.get_calendar_page(target_year, target_month, use_cache)

            # Extract event IDs
            event_ids = self.extract_event_ids(html_content)
            all_event_ids.extend(event_ids)

        # Remove duplicates and sort
        all_event_ids = sorted(list(set(all_event_ids)))
        self.logger.info(f"Total unique events to process: {len(all_event_ids)}")

        # Download iCal files for all events
        ical_contents = []
        for event_id in all_event_ids:
            ical_content = self.download_event_ical(event_id, use_cache)
            if ical_content:
                ical_contents.append(ical_content)

            # Be respectful - small delay between requests
            time.sleep(0.5)

        # Merge all iCal files
        merged_calendar = self.merge_ical_files(ical_contents)

        # Save merged calendar
        output_path = Path(output_file)
        output_path.write_bytes(merged_calendar.to_ical())
        self.logger.info(f"Saved merged calendar to: {output_path}")

        return str(output_path)


def main():
    """
    Main function to run the scraper.
    """
    parser = argparse.ArgumentParser(
        description="Extract events from LNHS calendar and generate consolidated iCal file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Scrape current and next month
  %(prog)s --year 2025 --months 3       # Scrape 3 months starting from current month in 2025
  %(prog)s --output my_calendar.ics     # Save to specific file
  %(prog)s --no-cache                   # Force re-download all data
""",
    )

    parser.add_argument(
        "--year", type=int, help="Year to scrape (defaults to current year)"
    )

    parser.add_argument(
        "--months", type=int, default=2, help="Number of months to scrape (default: 2)"
    )

    parser.add_argument(
        "--output",
        default="lnhs_events.ics",
        help="Output calendar file (default: lnhs_events.ics)",
    )

    parser.add_argument(
        "--cache-dir", default="cache", help="Cache directory (default: cache)"
    )

    parser.add_argument(
        "--no-cache", action="store_true", help="Force re-download all data"
    )
    
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)


    # Create scraper instance
    scraper = LNHSCalendarScraper(cache_dir=args.cache_dir)

    # Run scraper
    try:
        output_file = scraper.scrape_calendar(
            year=args.year,
            month_range=args.months,
            output_file=args.output,
            use_cache=not args.no_cache,
        )
        print(f"Successfully generated calendar: {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()

