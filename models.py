import io
import uuid
from datetime import datetime

import discord
from peewee import *
from peewee import ModelSelect

db = SqliteDatabase("db.sqlite3")


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class LinkCategory(BaseModel):
    channel = IntegerField()
    name = CharField()

    @classmethod
    def get_categories(cls, channel: int, category: str = None) -> ModelSelect:
        categories: ModelSelect = cls.select().where(LinkCategory.channel == channel)
        return categories.where(LinkCategory.name == category) if category else categories

    @classmethod
    def has_links(cls, channel: int, category: str = None) -> bool:
        for category in cls.get_categories(channel, category=category):
            if category.links.count() > 0:
                return True

        return False

    def append_field(self, embed: discord.Embed) -> None:
        value = ""
        for link in self.links:
            value += f"- [{link.title}]({link.link})\n"

        if len(value) > 1024:
            value = value[:1023]

        embed.add_field(name=self.name, value=value, inline=False)


class Link(BaseModel):
    link = CharField()
    title = CharField()
    category = ForeignKeyField(LinkCategory, backref='links')


class Appointment(BaseModel):
    channel = IntegerField()
    message = IntegerField()
    date_time = DateTimeField()
    reminder = IntegerField()
    title = CharField()
    description = CharField()
    author = IntegerField()
    recurring = IntegerField()
    reminder_sent = BooleanField()
    uuid = UUIDField(unique=True)

    def get_embed(self) -> discord.Embed:
        attendees = self.attendees
        embed = discord.Embed(title=self.title,
                              description=f"Wenn du eine Benachrichtigung zum Beginn des Termins"
                                          f"{f', sowie {self.reminder} Minuten vorher, ' if self.reminder > 0 else f''}"
                                          f" erhalten möchtest, reagiere mit :thumbsup: auf diese Nachricht.",
                              color=19607)

        if len(self.description) > 0:
            embed.add_field(name="Beschreibung", value=self.description, inline=False)
        embed.add_field(name="Startzeitpunkt", value=f"<t:{int(self.date_time.timestamp())}:F>", inline=False)
        if self.reminder > 0:
            embed.add_field(name="Benachrichtigung", value=f"{self.reminder} Minuten vor dem Start", inline=False)
        if self.recurring > 0:
            embed.add_field(name="Wiederholung", value=f"Alle {self.recurring} Tage", inline=False)
        if len(attendees) > 0:
            embed.add_field(name=f"Teilnehmerinnen ({len(attendees)})",
                            value=",".join([f"<@{attendee.member_id}>" for attendee in attendees]))

        return embed

    def get_ics_file(self) -> io.BytesIO:
        fmt: str = "%Y%m%dT%H%M"
        appointment: str = f"BEGIN:VCALENDAR\n" \
                           f"PRODID:Boty McBotface\n" \
                           f"VERSION:2.0\n" \
                           f"BEGIN:VTIMEZONE\n" \
                           f"TZID:Europe/Berlin\n" \
                           f"BEGIN:DAYLIGHT\n" \
                           f"TZOFFSETFROM:+0100\n" \
                           f"TZOFFSETTO:+0200\n" \
                           f"TZNAME:CEST\n" \
                           f"DTSTART:19700329T020000\n" \
                           f"RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3\n" \
                           f"END:DAYLIGHT\n" \
                           f"BEGIN:STANDARD\n" \
                           f"TZOFFSETFROM:+0200\n" \
                           f"TZOFFSETTO:+0100\n" \
                           f"TZNAME:CET\n" \
                           f"DTSTART:19701025T030000\n" \
                           f"RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10\n" \
                           f"END:STANDARD\n" \
                           f"END:VTIMEZONE\n" \
                           f"BEGIN:VEVENT\n" \
                           f"DTSTAMP:{datetime.now().strftime(fmt)}00Z\n" \
                           f"UID:{self.uuid}\n" \
                           f"SUMMARY:{self.title}\n"
        appointment += f"RRULE:FREQ=DAILY;INTERVAL={self.recurring}\n" if self.recurring else f""
        appointment += f"DTSTART;TZID=Europe/Berlin:{self.date_time.strftime(fmt)}00\n" \
                       f"DTEND;TZID=Europe/Berlin:{self.date_time.strftime(fmt)}00\n" \
                       f"TRANSP:OPAQUE\n" \
                       f"BEGIN:VALARM\n" \
                       f"ACTION:DISPLAY\n" \
                       f"TRIGGER;VALUE=DURATION:-PT{self.reminder}M\n" \
                       f"DESCRIPTION:{self.description}\n" \
                       f"END:VALARM\n" \
                       f"END:VEVENT\n" \
                       f"END:VCALENDAR"
        ics_file: io.BytesIO = io.BytesIO(appointment.encode("utf-8"))
        return ics_file


class Attendee(BaseModel):
    appointment = ForeignKeyField(Appointment, backref='attendees')
    member_id = IntegerField()


db.create_tables([LinkCategory, Link, Appointment, Attendee], safe=True)
