from typing import Iterable
from loguru import logger
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from datetime import date, timedelta, datetime


def init_calendar(email_id: str) -> GoogleCalendar:
    return GoogleCalendar(email_id)


def free_times(cal: GoogleCalendar) -> Iterable[str]:

    today = datetime.now()

    # Calculate two weeks from today
    two_weeks_from_now = today + timedelta(weeks=2)

    # Generate a list of dates from today to two weeks from now
    available_dates = [
        today + timedelta(days=i) for i in range((two_weeks_from_now - today).days + 1)
    ]

    events = cal.get_events(today, two_weeks_from_now)
    event_dates = [event.start.strftime("%Y-%m-%d") for event in events]

    # Convert the available dates back to strings (ISO format)
    available_dates = [date.strftime("%Y-%m-%d") for date in available_dates]

    # Filter out the event dates from the available dates
    available_dates = [
        date
        for date in available_dates
        if date not in [str(event) for event in event_dates]
    ]
    return available_dates


def create_event(cal: GoogleCalendar, start: date, summary: str) -> None:
    logger.debug("creating event")
    event = Event(summary=summary, start=start)
    cal.add_event(event)
    logger.debug("Exiting function")
