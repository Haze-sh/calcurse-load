import sys
import os
import json
import argparse
from itertools import chain
from dataclasses import dataclass
from typing import List, Iterator, Any, Dict, Optional
from datetime import date, timedelta

from lxml import etree, cssselect, html
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar

default_credential_file = os.path.join(
    os.environ["HOME"], ".credentials", "credentials.json"
)

Json = Dict[str, Any]

ATTENDEE_KEYS = ["email", "response_status"]


def create_calendar(email: str, credential_file: str) -> GoogleCalendar:
    return GoogleCalendar(email, credential_file, token_path=os.path.join(os.environ["HOME"], ".credentials", f"{email}.pickle"))


def n_days(days: int):
    """Get the date, for n days into the future"""
    return date.today() + timedelta(days=days)


def parse_args():
    parser = argparse.ArgumentParser(description="Export Google Calendar events")
    required = parser.add_argument_group("required options")
    parser.add_argument("--email", help="Google Email to export", required=True)
    parser.add_argument(
        "--credential-file",
        help="Google credential file",
        default=default_credential_file,
    )
    parser.add_argument(
        "--end-days",
        help="Specify how many days into the future to get events for (if we went forever, repeating events would be there in 2050) [default: 90]",
        default=90,
    )
    return parser.parse_args()


def _parse_html_description(htmlstr: Optional[str]) -> Json:
    data = {"text": None, "links": []}
    if htmlstr is None:
        return data
    root = html.fromstring(htmlstr)
    # filter all 'a' elements, get the link values, chain them together and remove items with no links
    data["links"] = list(
        filter(
            lambda h: h is not None,
            chain(*[link.values() for link in root.cssselect("a")]),
        )
    )
    data["text"] = "\n".join(map(str.strip, root.itertext()))
    return data


def event_to_dict(e: Event) -> Json:
    return {
        "summary": e.summary,
        "start": e.start.timestamp(),
        "end": e.end.timestamp(),
        "event_id": e.event_id,
        "description": _parse_html_description(e.description),
        "location": e.location,
        "recurrence": e.recurrence,
        "attendees": [
            {key: getattr(att, key) for key in ATTENDEE_KEYS} for att in e.attendees
        ],
    }


# get events from 1900 to now + args.end_days
def get_events(args) -> Iterator[Event]:
    cal = create_calendar(args.email, args.credential_file)
    yield from cal.get_events(date(1900, 1, 1), n_days(args.end_days))


def main():
    args = parse_args()
    if not os.path.exists(args.credential_file):
        print(
            f"Credential file at {args.credential_file} doesn't exist. Put it there or provide --credential-file"
        )
        sys.exit(1)
    print(json.dumps(list(map(event_to_dict, get_events(args)))))


if __name__ == "__main__":
    main()
