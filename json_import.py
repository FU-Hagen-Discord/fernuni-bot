import json
import uuid
from datetime import datetime

import models


def import_links(json_file: str) -> None:
    file = open(json_file, mode="r")
    links = json.load(file)

    for channel, categories in links.items():
        for category, links in categories.items():
            category = category.capitalize()
            db_category = models.LinkCategory.get_or_create(channel=int(channel), name=category)
            for title, link in links.items():
                models.Link.create(link=link, title=title, category=db_category[0].id)


def import_appointments(json_file: str) -> None:
    file = open(json_file, mode="r")
    appointments = json.load(file)

    for channel, channel_appointments in appointments.items():
        for message, appointment in channel_appointments.items():
            date_time = datetime.strptime(appointment["date_time"], "%d.%m.%Y %H:%M")
            reminder = appointment["reminder"]
            title = appointment["title"]
            author = appointment["author_id"]
            recurring = appointment.get("recurring") if appointment.get("recurring") else 0

            db_appointment = models.Appointment.get_or_create(channel=int(channel), message=int(message),
                                                              date_time=date_time, reminder=reminder, title=title,
                                                              description="", author=author, recurring=recurring,
                                                              reminder_sent=False, uuid=uuid.uuid4())

            if appointment.get("attendees"):
                for attendee in appointment.get("attendees"):
                    models.Attendee.create(appointment=db_appointment[0].id, member_id=attendee)


if __name__ == "__main__":
    """
    Make sure to create a database backup before you import data from json files.
    """
    # import_links("data/links.json")
    # import_appointments("data/appointments.json")
