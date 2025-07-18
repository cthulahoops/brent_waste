#!/usr/bin/env python3
"""
Script to extract waste collection dates from Brent Council website.
Uses the discovered API endpoint with polling for data.
"""

import argparse
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def get_collection_data(property_id, max_attempts=10, cache_html=False):
    """
    Poll the Brent Council API endpoint until data loads.
    """
    url = f"https://recyclingservices.brent.gov.uk/waste/{property_id}"

    headers = {
        "Referer": f"https://recyclingservices.brent.gov.uk/waste/{property_id}",
    }

    session = requests.Session()

    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts}: Fetching collection data...")

            # Try with page_loading parameter
            response = session.get(f"{url}?page_loading=1", headers=headers, timeout=10)

            if response.status_code == 200:
                content = response.text

                # Write HTML to file for analysis if caching enabled
                if cache_html:
                    filename = f"brent_waste_{property_id}_attempt_{attempt + 1}.html"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"  Saved HTML to {filename}")

                # Check if still loading
                if "Loading your bin days..." in content:
                    print("  Still loading, waiting 3 seconds...")
                    time.sleep(3)
                    continue

                # Parse the HTML content
                soup = BeautifulSoup(content, "html.parser")

                # Look for collection information
                collection_data = extract_collection_dates(soup)

                if collection_data:
                    return collection_data
                print("  No collection data found in response")

            else:
                print(f"  HTTP {response.status_code}: {response.reason}")

        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")

        time.sleep(2)  # Wait before next attempt

    return None


def _extract_dates_with_regex(soup):
    """
    Extract dates using regex patterns as fallback.
    """
    # Date patterns for regex matching
    weekday_pattern = (
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?"
        r"\s+\d{1,2}(?:st|nd|rd|th)?\s+"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"(?:\s+\d{4})?\b"
    )
    date_only_pattern = (
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{4}\b"
    )
    date_patterns = [weekday_pattern, date_only_pattern]

    text_content = soup.get_text()
    found_dates = set()

    for pattern in date_patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        found_dates.update(matches)

    return sorted(list(found_dates)) if found_dates else []


def extract_collection_dates(soup):
    """
    Extract collection dates from the parsed HTML.
    """
    collections = []

    # Find all waste service sections
    waste_sections = soup.find_all("h3", class_="govuk-heading-m waste-service-name")

    for section in waste_sections:
        service_name = section.get_text().strip()

        # Find the next collection date for this service
        next_section = section.find_next_sibling("div", class_="govuk-grid-row")
        if next_section:
            # Look for "Next collection" row
            next_collection_row = next_section.find("dt", string="Next collection")
            if next_collection_row:
                next_collection_value = next_collection_row.find_next("dd")
                if next_collection_value:
                    date_text = next_collection_value.get_text().strip()
                    if date_text:
                        collections.append(f"{service_name}: {date_text}")

            # Also look for "Last collection" for completeness
            last_collection_row = next_section.find("dt", string="Last collection")
            if last_collection_row:
                last_collection_value = last_collection_row.find_next("dd")
                if last_collection_value:
                    date_text = last_collection_value.get_text().strip()
                    if date_text:
                        collections.append(f"{service_name} (last): {date_text}")

            # Look for "Renewal" date (typically for garden waste)
            renewal_row = next_section.find("dt", string="Renewal")
            if renewal_row:
                renewal_value = renewal_row.find_next("dd")
                if renewal_value:
                    date_text = renewal_value.get_text().strip()
                    if date_text:
                        collections.append(f"{service_name} (renewal): {date_text}")

    # If no structured data found, fall back to regex pattern matching
    if not collections:
        collections = _extract_dates_with_regex(soup)

    return collections


def parse_collection_date(date_text):
    """
    Parse collection date text and return a datetime object with time if available.
    """
    # Clean up the date text
    date_text = date_text.strip()

    # Extract time information if present
    time_part = None
    if " at " in date_text:
        parts = date_text.split(" at ")
        date_text = parts[0]
        if len(parts) > 1:
            time_info = parts[1].strip()
            # Remove adjustment notes from time part
            if "(this collection was adjusted" in time_info:
                time_info = time_info.split("(this collection was adjusted")[0].strip()
            time_part = time_info

    # Remove adjustment notes from date part
    if "(this collection was adjusted" in date_text:
        date_text = date_text.split("(this collection was adjusted")[0].strip()

    # Remove trailing comma
    date_text = date_text.rstrip(",")

    # Parse different date formats
    try:
        # Try "Tuesday, 15th July" format
        if "," in date_text:
            parts = date_text.split(", ")
            if len(parts) >= 2:
                date_part = parts[1].strip()
                # Handle ordinal numbers (15th -> 15)
                date_part = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", date_part)

                # Add current year if not present
                if not re.search(r"\d{4}", date_part):
                    current_year = datetime.now().year
                    date_part = f"{date_part} {current_year}"

                # Parse the date
                date_obj = datetime.strptime(date_part, "%d %B %Y")

                # Add time if available
                if time_part:
                    time_obj = parse_time(time_part)
                    if time_obj:
                        date_obj = date_obj.replace(
                            hour=time_obj.hour, minute=time_obj.minute
                        )

                return date_obj

        # Try other formats
        date_text = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", date_text)

        # Try "15 July 2024" format
        try:
            date_obj = datetime.strptime(date_text, "%d %B %Y")
            if time_part:
                time_obj = parse_time(time_part)
                if time_obj:
                    date_obj = date_obj.replace(
                        hour=time_obj.hour, minute=time_obj.minute
                    )
            return date_obj
        except ValueError:
            pass

        # Try "15 July" format (add current year)
        try:
            current_year = datetime.now().year
            date_obj = datetime.strptime(f"{date_text} {current_year}", "%d %B %Y")
            if time_part:
                time_obj = parse_time(time_part)
                if time_obj:
                    date_obj = date_obj.replace(
                        hour=time_obj.hour, minute=time_obj.minute
                    )
            return date_obj
        except ValueError:
            pass

    except (ValueError, TypeError):
        pass

    return None


def parse_time(time_text):
    """
    Parse time text like "11:10am" and return a datetime object with time.
    """
    if not time_text:
        return None

    try:
        # Clean up the time text
        time_text = time_text.strip()

        # Handle formats like "11:10am", "8:38am", " 8:42am"
        time_text = time_text.strip()

        # Try parsing with am/pm
        if time_text.lower().endswith("am") or time_text.lower().endswith("pm"):
            return datetime.strptime(time_text, "%I:%M%p")

        # Try parsing 24-hour format
        if ":" in time_text:
            return datetime.strptime(time_text, "%H:%M")

    except ValueError:
        pass

    return None


def generate_ical(collections):
    """
    Generate iCal format from collection data.
    Groups multiple collections on the same date into single events.
    """
    ical_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Brent Council//Waste Collection Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    # Group collections by date
    collections_by_date = {}
    renewal_events = []

    for collection in collections:
        if ": " in collection:
            service_name, date_text = collection.split(": ", 1)
            service_name = service_name.replace("\n", " ").strip()

            parsed_date = parse_collection_date(date_text)
            if parsed_date:
                date_str = parsed_date.strftime("%Y%m%d")

                # Handle renewal events separately
                if "(renewal)" in service_name.lower():
                    renewal_events.append((service_name, parsed_date, date_text))
                else:
                    # Group regular collections by date
                    if date_str not in collections_by_date:
                        collections_by_date[date_str] = {
                            "date": parsed_date,
                            "services": [],
                            "has_times": False,
                        }

                    collections_by_date[date_str]["services"].append(
                        {
                            "name": service_name,
                            "time": (
                                parsed_date
                                if parsed_date.hour != 0 or parsed_date.minute != 0
                                else None
                            ),
                            "original_text": date_text,
                        }
                    )

                    if parsed_date.hour != 0 or parsed_date.minute != 0:
                        collections_by_date[date_str]["has_times"] = True

    # Create events for grouped collections
    for date_str, group in collections_by_date.items():
        services = group["services"]
        date_obj = group["date"]
        has_times = group["has_times"]

        if len(services) == 1:
            # Single service, use original format
            service = services[0]
            clean_name = (
                service["name"].replace("collection", "").replace("waste", "").strip()
            )
            clean_name = clean_name.replace(
                "(blue sacks)", ""
            ).strip()  # Remove (blue sacks)
            clean_name = " ".join(
                clean_name.split()
            )  # Replace multiple spaces with single space

            uid = f"{service['name'].replace(' ', '_')}_{date_str}@brent.gov.uk"
            summary = f"Waste Collection: {clean_name}"
            description = f"Waste collection: {clean_name}"

            if service["time"]:
                datetime_str = service["time"].strftime("%Y%m%dT%H%M%S")
                dtstart = f"DTSTART:{datetime_str}"
            else:
                dtstart = f"DTSTART;VALUE=DATE:{date_str}"
        else:
            # Multiple services, create consolidated event
            service_names = []
            for s in services:
                name = s["name"].replace("collection", "").replace("waste", "").strip()
                name = name.replace("(blue sacks)", "").strip()  # Remove (blue sacks)
                name = " ".join(
                    name.split()
                )  # Replace multiple spaces with single space
                service_names.append(name)

            uid = f"collections_{date_str}@brent.gov.uk"
            summary = f"Waste Collections: {', '.join(service_names)}"

            if has_times:
                # Create all-day event with times in description
                dtstart = f"DTSTART;VALUE=DATE:{date_str}"
                time_details = []
                for service in services:
                    clean_name = (
                        service["name"]
                        .replace("collection", "")
                        .replace("waste", "")
                        .strip()
                    )
                    clean_name = clean_name.replace(
                        "(blue sacks)", ""
                    ).strip()  # Remove (blue sacks)
                    clean_name = " ".join(
                        clean_name.split()
                    )  # Replace multiple spaces with single space
                    if service["time"]:
                        time_str = service["time"].strftime("%I:%M%p").lower()
                        time_details.append(f"+ {clean_name}: {time_str}")
                    else:
                        time_details.append(f"+ {clean_name}")

                description = (
                    f"Waste collections:\\n{chr(10).join(time_details)}".replace(
                        "\n", "\\n"
                    )
                )
            else:
                # All-day event without specific times
                dtstart = f"DTSTART;VALUE=DATE:{date_str}"
                description = f"Waste collections:\\n{chr(10).join(f'+ {name}' for name in service_names)}".replace(
                    "\n", "\\n"
                )

        # Create event
        ical_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                dtstart,
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                "CATEGORIES:Waste Collection",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                "END:VEVENT",
            ]
        )

    # Add renewal events separately
    for service_name, parsed_date, date_text in renewal_events:
        date_str = parsed_date.strftime("%Y%m%d")
        clean_name = service_name.replace("collection", "").strip()
        clean_name = clean_name.replace(
            "(blue sacks)", ""
        ).strip()  # Remove (blue sacks)
        clean_name = " ".join(
            clean_name.split()
        )  # Replace multiple spaces with single space

        # Make renewal events more explicit
        if "(renewal)" in clean_name.lower():
            clean_name = clean_name.replace("(renewal)", "").strip()
            clean_name = f"{clean_name} Renewal"

        uid = f"{service_name.replace(' ', '_')}_{date_str}@brent.gov.uk"

        if parsed_date.hour == 0 and parsed_date.minute == 0:
            dtstart = f"DTSTART;VALUE=DATE:{date_str}"
        else:
            datetime_str = parsed_date.strftime("%Y%m%dT%H%M%S")
            dtstart = f"DTSTART:{datetime_str}"

        ical_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                dtstart,
                f"SUMMARY:{clean_name}",
                f"DESCRIPTION:{clean_name}",
                "CATEGORIES:Waste Collection",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                "END:VEVENT",
            ]
        )

    ical_lines.append("END:VCALENDAR")
    return "\n".join(ical_lines)


def test_with_saved_html(filename, output_file=None):
    """
    Test the extraction using a saved HTML file.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        collection_data = extract_collection_dates(soup)

        if collection_data:
            print(f"Found {len(collection_data)} collection dates/info:")
            print("-" * 50)
            for i, item in enumerate(collection_data, 1):
                print(f"{i:2d}. {item}")

            # Generate and save iCal if output file specified
            if output_file:
                ical_content = generate_ical(collection_data)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(ical_content)
                print(f"\nSaved iCal format to: {output_file}")
        else:
            print("No collection data found in the saved HTML file.")

    except FileNotFoundError:
        print(f"File {filename} not found.")
    except (IOError, OSError) as e:
        print(f"Error reading file: {e}")


def main():
    """
    Main function to run the scraper.
    """
    parser = argparse.ArgumentParser(
        description="Extract waste collection dates from Brent Council website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 1234567            # Use specific property ID
  %(prog)s saved.html         # Test with saved HTML file
  %(prog)s 1234567 -o calendar.ics  # Save calendar to specific file
  %(prog)s 1234567 --cache-html  # Cache HTML files for debugging
  BRENT_PROPERTY_ID=1234567 %(prog)s  # Use environment variable
""",
    )

    parser.add_argument(
        "property_id",
        nargs="?",
        help="Property ID to lookup or HTML file to test with (uses BRENT_PROPERTY_ID env var if not provided)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output calendar file (e.g., calendar.ics). If not specified, no calendar file is created.",
    )

    parser.add_argument(
        "--cache-html",
        action="store_true",
        help="Cache HTML files for debugging. If not specified, HTML files are not saved.",
    )

    args = parser.parse_args()

    # Get property_id from args or environment variable
    property_id = args.property_id or os.environ.get("BRENT_PROPERTY_ID")
    if not property_id:
        parser.error(
            "Property ID is required either as argument or BRENT_PROPERTY_ID environment variable"
        )

    # Check if it's a file path (contains .html)
    if property_id.endswith(".html"):
        print(f"Testing with saved HTML file: {property_id}")
        print("=" * 60)
        test_with_saved_html(property_id, args.output)
        return
    print(f"Extracting waste collection dates for property: {property_id}")
    print("=" * 60)

    collection_data = get_collection_data(property_id, cache_html=args.cache_html)

    if collection_data:
        print(f"\nFound {len(collection_data)} collection dates/info:")
        print("-" * 50)

        for i, item in enumerate(collection_data, 1):
            print(f"{i:2d}. {item}")

        # Generate and save iCal if output file specified
        if args.output:
            ical_content = generate_ical(collection_data)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(ical_content)
            print(f"\nSaved iCal format to: {args.output}")
    else:
        print("\nNo collection data found.")
        print("The property ID may be invalid or the service may be unavailable.")
        print("Try checking the URL manually in a browser.")


if __name__ == "__main__":
    main()
