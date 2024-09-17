import json
import os
import uuid
import datetime

import discord
from dotenv import load_dotenv

import models
from models import Appointment
from views.appointment_view import AppointmentView


def import_links(json_file: str) -> None:
    file = open(json_file, mode="r")
    links = json.load(file)

    for channel, categories in links.items():
        for category, links in categories.items():
            category = category.capitalize()
            db_category = models.LinkCategory.get_or_create(channel=int(channel), name=category)
            for title, link in links.items():
                link = link[1:-1] if link[0] == "<" and link[-1] == ">" else link
                models.Link.create(url=link, title=title, category=db_category[0].id)


def import_news(json_file: str) -> None:
    file = open(json_file, mode="r")
    news = json.load(file)

    for link, date in news.items():
        models.News.create(link=link, date=date)


def import_commands(json_file: str) -> None:
    file = open(json_file, mode="r")
    commands = json.load(file)

    for command, data in commands.items():
        db_command = models.Command.get_or_create(command=command, description=data["description"])
        for text in data["data"]:
            models.CommandText.create(text=text, command=db_command[0].id)


def import_courses(json_file: str) -> None:
    file = open(json_file, mode="r")
    courses = json.load(file)

    for course in courses:
        models.Course.get_or_create(name=course["name"], short=course["short"], url=course["url"],
                                    role_id=int(course["role"]))


async def import_appointments(json_file: str) -> None:
    file = open(json_file, mode="r")
    appointments = json.load(file)

    for channel_id, messages in appointments.items():
        for message_id, appointment in messages.items():
            date_time = datetime.datetime.strptime(appointment["date_time"], "%d.%m.%Y %H:%M")
            reminder_sent = True if appointment["reminder"] == 0 and appointment.get(
                "original_reminder") is not None else False

            app = models.Appointment.create(channel=int(channel_id), message=int(message_id), date_time=date_time, appointment=appointment["reminder"], description="", author=appointment["author_id"],
                                            recurring=appointment.get("recurring", 0), reminder_sent=reminder_sent,
                                            uuid=uuid.uuid4())
            channel = await client.fetch_channel(app.channel_id)
            message = await channel.fetch_message(app.message)
            for reaction in message.reactions:
                    if reaction.emoji == "👍":
                        async for user in reaction.users():
                            if not user.bot:
                                models.Attendee.create(appointment=app, member_id=user.id)
            new_msg = await channel.send(embed=appointment.get_embed(0), view=AppointmentView())
            Appointment.update(message=new_msg.id).where(Appointment.id == app.id).execute()


load_dotenv()
client = discord.Client(intents=discord.Intents.all())


@client.event()
async def on_ready():
    """
        Make sure to create a database backup before you import data from json files.
    """
    # import_links("data/links.json")
    # import_news("data/news.json")
    # import_commands("data/text_commands.json")
    # import_courses("data/courses_of_studies.json")
    await import_appointments("data/appointments.json")


client.run(os.getenv("DISCORD_TOKEN"))
