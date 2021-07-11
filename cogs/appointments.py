import asyncio
import datetime
import os
import uuid

import discord
from discord.ext import tasks, commands
from tinydb import where

import utils
from cogs.help import help, handle_error, help_category


def get_ics_file(title, date_time, reminder, recurring):
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
                  f"UID:{uuid.uuid4()}\n" \
                  f"SUMMARY:{title}\n"
    appointment += f"RRULE:FREQ=DAILY;INTERVAL={recurring}\n" if recurring else f""
    appointment += f"DTSTART;TZID=Europe/Berlin:{date_time.strftime(fmt)}00\n" \
                   f"DTEND;TZID=Europe/Berlin:{date_time.strftime(fmt)}00\n" \
                   f"TRANSP:OPAQUE\n" \
                   f"BEGIN:VALARM\n" \
                   f"ACTION:DISPLAY\n" \
                   f"TRIGGER;VALUE=DURATION:-PT{reminder}M\n" \
                   f"DESCRIPTION:Halloooo, dein Termin findest bald statt!!!!\n" \
                   f"END:VALARM\n" \
                   f"END:VEVENT\n" \
                   f"END:VCALENDAR"
    ics_file = io.BytesIO(appointment.encode("utf-8"))
    return ics_file


@help_category("appointments", "Appointments", "Mit Appointments kannst du Termine zu einem Kanal hinzufügen. "
                                               "Sehr praktisches Feature zum Organisieren von Lerngruppen.")
class Appointments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fmt = os.getenv("DISCORD_DATE_TIME_FORMAT")
        self.timer.start()

    @property
    def table(self):
        return self.bot.db.table('calendar')

    @tasks.loop(minutes=1)
    async def timer(self):
        now = datetime.datetime.now()

        for event in self.table.all():
            date_time = datetime.datetime.strptime(event["date_time"], self.fmt)
            remind_at = date_time - datetime.timedelta(minutes=event["reminder"])

            if now >= remind_at:
                try:
                    event_started = False
                    channel = await self.bot.fetch_channel(event["channel_id"])
                    message = await channel.fetch_message(event["message_id"])
                    reactions = message.reactions
                    diff = int(round(((date_time - now).total_seconds() / 60), 0))
                    answer = f"Benachrichtigung!\nDer Termin \"{event['title']}\" ist "

                    if event["reminder"] > 0 and diff > 0:
                        answer += f"in {diff} Minuten fällig."
                        if (reminder := event.get("reminder")) and event.get("recurring"):
                            event["original_reminder"] = str(reminder)
                        event["reminder"] = 0
                    else:
                        answer += f"jetzt fällig. :loudspeaker: "
                        event_started = True

                    answer += f"\n"
                    for reaction in reactions:
                        if reaction.emoji == "👍":
                            async for user in reaction.users():
                                if user != self.bot.user:
                                    answer += f"<@!{str(user.id)}> "

                    await channel.send(answer)
                    if event_started:
                        await self.event_started(event)
                        await message.delete()
                except discord.errors.NotFound:
                    self.table.remove(where("message_id") == event["message_id"])

    async def event_started(self, event):
        if recurring := event.get("recurring"):
            channel = await self.bot.fetch_channel(event["channel_id"])
            date_time_str = event["date_time"]
            date_time = datetime.datetime.strptime(date_time_str, self.fmt)
            new_date_time = date_time + datetime.timedelta(minutes=recurring)
            new_date_time_str = new_date_time.strftime(self.fmt)
            splitted_new_date_time_str = new_date_time_str.split(" ")
            reminder = event.get("original_reminder")
            reminder = reminder if reminder else 0
            await self.add_appointment(channel, event["author_id"],
                                       splitted_new_date_time_str[0],
                                       splitted_new_date_time_str[1],
                                       str(reminder),
                                       event["title"],
                                       event["recurring"])

        self.table.remove(where("message_id") == event["message_id"])

    @timer.before_loop
    async def before_timer(self):
        await asyncio.sleep(60 - datetime.datetime.now().second)

    @help(
        category="appointments",
        brief="Fügt eine neue Erinnerung zu einem Kanal hinzu.",
        example="!add-appointment 20.12.2021 10:00 0 \"Toller Event\" 7",
        parameters={
            "date": "Datum des Termins im Format DD.MM.YYYY (z. B. 22.10.2022).",
            "time": "Uhrzeit des Termins im Format hh:mm (z. B. 10:00).",
            "reminder": "Anzahl an Minuten die vor dem Termin erinnert werden soll.",
            "title": "der Titel des Termins (in Anführungszeichen).",
            "recurring": "*(optional)* Interval für die Terminwiederholung in Tagen"
        }
    )
    @commands.command(name="add-appointment")
    async def cmd_add_appointment(self, ctx, date, time, reminder, title, recurring: int = None):
        await self.add_appointment(ctx.channel, ctx.author.id, date, time, reminder, title, recurring)

    async def add_appointment(self, channel, author_id, date, time, reminder, title, recurring: int = None):
        """ Add appointment to a channel """

        try:
            date_time = datetime.datetime.strptime(f"{date} {time}", self.fmt)
        except ValueError:
            await channel.send("Fehler! Ungültiges Datums und/oder Zeit Format!")
            return

        if not utils.is_valid_time(reminder):
            await channel.send("Fehler! Benachrichtigung in ungültigem Format!")
            return
        else:
            reminder = utils.to_minutes(reminder)

        embed = discord.Embed(title="Neuer Termin hinzugefügt!",
                              description=f"Wenn du eine Benachrichtigung zum Beginn des Termins"
                                          f"{f', sowie {reminder} Minuten vorher, ' if reminder > 0 else f''} "
                                          f"erhalten möchtest, reagiere mit :thumbsup: auf diese Nachricht.",
                              color=19607)

        embed.add_field(name="Titel", value=title, inline=False)
        embed.add_field(name="Startzeitpunkt", value=f"{date_time.strftime(self.fmt)}", inline=False)
        if reminder > 0:
            embed.add_field(name="Benachrichtigung", value=f"{reminder} Minuten vor dem Start", inline=False)
        if recurring:
            embed.add_field(name="Wiederholung", value=f"Alle {recurring} Tage", inline=False)

        message = await channel.send(embed=embed, file=discord.File(get_ics_file(title, date_time, reminder, recurring),
                                                                    filename=f"{title}.ics"))
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")

        self.table.insert({"channel_id": channel.id, "message_id": message.id,
                           "date_time": date_time.strftime(self.fmt), "reminder": reminder, "title": title,
                           "author_id": author_id, "recurring": recurring})

    @help(
        category="appointments",
        brief="Zeigt alle Termine des momentanen Kanals an."
    )
    @commands.command(name="appointments")
    async def cmd_appointments(self, ctx):
        """ List (and link) all Appointments in the current channel """

        if events := self.table.search(where("channel_id") == ctx.channel.id):
            answer = f'Termine dieses Channels:\n'
            for event in events:
                try:
                    message = await ctx.channel.fetch_message(event["message_id"])
                    answer += f'{event["date_time"]}: {event["title"]} => ' \
                              f'{message.jump_url}\n'
                except discord.errors.NotFound:
                    self.table.remove(where("message_id") == event["message_id"])
            await ctx.channel.send(answer)
        else:
            await ctx.send("Für diesen Channel existieren derzeit keine Termine")

    async def handle_reactions(self, payload):
        if event := self.table.get(where("message_id") == payload.message_id):
            if payload.user_id == event["author_id"]:
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                await message.delete()
                self.table.remove(where("message_id") == event["message_id"])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.emoji.name in ["🗑️"]:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds) > 0 and message.embeds[0].title == "Neuer Termin hinzugefügt!":
                await self.handle_reactions(payload)

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
