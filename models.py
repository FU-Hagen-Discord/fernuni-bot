import datetime
import io
import uuid

import discord
from discord import Colour
from peewee import *
from peewee import ModelSelect

db = SqliteDatabase("db.sqlite3")


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class Settings(BaseModel):
    guild_id = IntegerField(default=0)
    greeting_channel_id = IntegerField(default=0)
    modmail_channel_id = IntegerField(default=0)
    news_url = CharField()
    news_channel_id = IntegerField(default=0)
    news_role_id = IntegerField(default=0)
    command_approval_channel_id = IntegerField(default=0)
    learninggroup_voice_category_id = IntegerField(default=0)
    voice_bitrate = IntegerField(default=0)
    thread_notification_role_id = IntegerField(default=0)


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


class Link(BaseModel):
    url = CharField()
    title = CharField()
    category = ForeignKeyField(LinkCategory, backref='links')


class News(BaseModel):
    link = CharField()
    date = CharField()


class Poll(BaseModel):
    question = CharField()
    author = IntegerField()
    channel = IntegerField()
    message = IntegerField()

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Umfrage", description=self.question)
        embed.add_field(name="Erstellt von", value=f'<@!{self.author}>', inline=False)
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        for choice in self.choices:
            name = f'{choice.emoji}  {choice.text}'
            value = f'{len(choice.participants)}'

            embed.add_field(name=name, value=value, inline=False)

        participants = {str(participant.member_id): 1 for participant in
                        PollParticipant.select().join(PollChoice, on=PollParticipant.poll_choice).where(
                            PollChoice.poll == self)}

        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name="Anzahl der Teilnehmer an der Umfrage", value=f"{len(participants)}", inline=False)

        return embed


class PollChoice(BaseModel):
    poll = ForeignKeyField(Poll, backref='choices')
    text = CharField()
    emoji = CharField()


class PollParticipant(BaseModel):
    poll_choice = ForeignKeyField(PollChoice, backref='participants')
    member_id = IntegerField()


class Command(BaseModel):
    guild_id = IntegerField()
    command = CharField(unique=True)
    description = CharField()


class CommandText(BaseModel):
    text = CharField()
    command = ForeignKeyField(Command, backref="texts")


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
    uuid = UUIDField(default=uuid.uuid4())

    def get_embed(self, state: int) -> discord.Embed:
        attendees = self.attendees
        description = (f"Wenn du eine Benachrichtigung zum Beginn des Termins "
                       f"{f', sowie {self.reminder} Minuten vorher, ' if self.reminder > 0 else f''}"
                       f" erhalten möchtest, verwende den \"Zusagen\" Button unter dieser Nachricht. "
                       f"Hast du bereits zugesagt und möchtest keine Benachrichtigung erhalten, "
                       f"kannst du den \"Absagen\" Button benutzen.") if state != 2 else ""
        emoji = "📅" if state == 0 else ("📣" if state == 1 else "✅")
        embed = discord.Embed(title=f"{emoji} {self.title} {'begint!!!' if state == 2 else ''}",
                              description=description)

        embed.color = Colour.green() if state == 0 else Colour.yellow() if state == 1 else 19607

        if len(self.description) > 0:
            embed.add_field(name="Beschreibung", value=self.description, inline=False)

        embed.add_field(name="Startzeitpunkt", value=self.get_start_time(state), inline=False)
        if self.reminder > 0 and state == 0:
            embed.add_field(name="Erinnerung", value=f"{self.reminder} Minuten vor dem Start", inline=False)
        if self.recurring > 0:
            embed.add_field(name="Wiederholung", value=f"Alle {self.recurring} Tage", inline=False)
        if len(attendees) > 0:
            embed.add_field(name=f"Teilnehmerinnen ({len(attendees)})",
                            value=",".join([f"<@{attendee.member_id}>" for attendee in attendees]))

        return embed

    def get_start_time(self, state) -> str:
        if state == 0:
            return f"<t:{int(self.date_time.timestamp())}:F>"
        elif state == 1:
            return f"<t:{int(self.date_time.timestamp())}:F> (<t:{int(self.date_time.timestamp())}:R>)"

        return "Jetzt!"

    def get_ics_file(self):
        fmt = "%Y%m%dT%H%M"
        appointment = f"BEGIN:VCALENDAR\n" \
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
                      f"DTSTAMP:{datetime.datetime.now().strftime(fmt)}00Z\n" \
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
        ics_file = io.BytesIO(appointment.encode("utf-8"))
        return ics_file


class Attendee(BaseModel):
    appointment = ForeignKeyField(Appointment, backref='attendees')
    member_id = IntegerField()


class Course(BaseModel):
    name = CharField()
    short = CharField()
    url = CharField()
    role_id = IntegerField()


class Module(BaseModel):
    number = IntegerField(primary_key=True)
    title = CharField()
    url = CharField()
    ects = CharField(null=True)
    effort = CharField(null=True)
    duration = CharField(null=True)
    interval = CharField(null=True)
    notes = CharField(null=True)
    requirements = CharField(null=True)


class Event(BaseModel):
    name = CharField()
    number = CharField()
    url = CharField()
    module = ForeignKeyField(Module, backref='events')


class Support(BaseModel):
    title = CharField()
    city = CharField()
    url = CharField()
    module = ForeignKeyField(Module, backref='support')


class Exam(BaseModel):
    name = CharField()
    type = CharField(null=True)
    requirements = CharField(null=True)
    weight = CharField(null=True)
    hard_requirements = CharField(null=True)
    module = ForeignKeyField(Module, backref='exams')


class Download(BaseModel):
    title = CharField()
    url = CharField()
    module = ForeignKeyField(Module, backref='downloads')


class Contact(BaseModel):
    name = CharField()
    module = ForeignKeyField(Module, backref='contacts')


db.create_tables(
    [Settings, LinkCategory, Link, News, Poll, PollChoice, PollParticipant, Command, CommandText, Appointment,
     Attendee, Course, Module, Event, Support, Exam, Download, Contact], safe=True)
