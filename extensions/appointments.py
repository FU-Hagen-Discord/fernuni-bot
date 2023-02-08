import asyncio
import io
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import NewType, Union

from discord import app_commands, errors, Embed, File, Interaction, VoiceChannel, StageChannel, TextChannel, \
    ForumChannel, CategoryChannel, Thread, PartialMessageable
from discord.ext import tasks, commands

Channel = NewType('Channel', Union[
    VoiceChannel, StageChannel, TextChannel, ForumChannel, CategoryChannel, Thread, PartialMessageable, None])


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
                  f"DTSTAMP:{datetime.now().strftime(fmt)}00Z\n" \
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


@app_commands.guild_only()
class Appointments(commands.GroupCog, name="appointments", description="Verwaltet Termine in Kanälen"):
    def __init__(self, bot):
        self.bot = bot
        self.fmt = os.getenv("DISCORD_DATE_TIME_FORMAT")
        self.timer.start()
        self.appointments = {}
        self.app_file = os.getenv("DISCORD_APPOINTMENTS_FILE")
        self.load_appointments()

    def load_appointments(self):
        appointments_file = open(self.app_file, mode='r')
        self.appointments = json.load(appointments_file)

    def save_appointments(self):
        appointments_file = open(self.app_file, mode='w')
        json.dump(self.appointments, appointments_file)

    @tasks.loop(minutes=1)
    async def timer(self):
        delete = []

        for channel_id, channel_appointments in self.appointments.items():
            channel = None
            for message_id, appointment in channel_appointments.items():
                now = datetime.now()
                date_time = datetime.strptime(appointment["date_time"], self.fmt)
                remind_at = date_time - timedelta(minutes=appointment["reminder"])

                if now >= remind_at:
                    try:
                        channel = await self.bot.fetch_channel(int(channel_id))
                        message = await channel.fetch_message(int(message_id))
                        reactions = message.reactions
                        diff = int(round(((date_time - now).total_seconds() / 60), 0))
                        answer = f"Benachrichtigung!\nDer Termin \"{appointment['title']}\" startet "

                        if appointment["reminder"] > 0 and diff > 0:
                            answer += f"<t:{int(date_time.timestamp())}:R>."
                            if (reminder := appointment.get("reminder")) and appointment.get("recurring"):
                                appointment["original_reminder"] = str(reminder)
                            appointment["reminder"] = 0
                        else:
                            answer += f"jetzt! :loudspeaker: "
                            delete.append(message_id)

                        answer += f"\n"
                        for reaction in reactions:
                            if reaction.emoji == "👍":
                                async for user in reaction.users():
                                    if user != self.bot.user:
                                        answer += f"<@!{str(user.id)}> "

                        await channel.send(answer)

                        if str(message.id) in delete:
                            await message.delete()
                    except errors.NotFound:
                        delete.append(message_id)

            if len(delete) > 0:
                for key in delete:
                    channel_appointment = channel_appointments.get(key)
                    if channel_appointment:
                        if channel_appointment.get("recurring"):
                            recurring = channel_appointment["recurring"]
                            date_time_str = channel_appointment["date_time"]
                            date_time = datetime.strptime(date_time_str, self.fmt)
                            new_date_time = date_time + timedelta(days=recurring)
                            new_date_time_str = new_date_time.strftime(self.fmt)
                            splitted_new_date_time_str = new_date_time_str.split(" ")
                            reminder = channel_appointment.get("original_reminder")
                            reminder = reminder if reminder else 0
                            await self.add_appointment(channel, channel_appointment["author_id"],
                                                       splitted_new_date_time_str[0],
                                                       splitted_new_date_time_str[1],
                                                       reminder,
                                                       channel_appointment["title"],
                                                       channel_appointment["recurring"])
                        channel_appointments.pop(key)
                self.save_appointments()

    @timer.before_loop
    async def before_timer(self):
        await asyncio.sleep(60 - datetime.now().second)

    @app_commands.command(name="add", description="Fügt dem Kanal einen neunen Termin hinzu.")
    @app_commands.describe(date="Tag des Termins (z. B. 21.10.2015).", time="Uhrzeit des Termins (z. B. 13:37).",
                           reminder="Wie viele Minuten bevor der Termin startet, soll eine Erinnerung verschickt werden?",
                           title="Titel des Termins",
                           recurring="In welchem Intervall (in Tagen) soll der Termin wiederholt werden?")
    async def cmd_add_appointment(self, interaction: Interaction, date: str, time: str, reminder: int, title: str,
                                  recurring: int = None):

        await interaction.response.defer(ephemeral=True)
        await self.add_appointment(interaction.channel, interaction.user.id, date, time, reminder, title, recurring)
        await interaction.edit_original_response(content="Termin erfolgreich erstellt!")

    # /appointments add date:31.08.2022 time:20:00 reminder:60 title:Test
    async def add_appointment(self, channel: Channel, author_id: int, date: str, time: str, reminder: int, title: str,
                              recurring: int = None) -> None:
        try:
            date_time = datetime.strptime(f"{date} {time}", self.fmt)
        except ValueError:
            await channel.send("Fehler! Ungültiges Datums und/oder Zeit Format!")
            return

        embed = self.get_embed(title, date_time, reminder, recurring)
        message = await channel.send(embed=embed, file=File(get_ics_file(title, date_time, reminder, recurring),
                                                            filename=f"{title}.ics"))
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")

        if str(channel.id) not in self.appointments:
            self.appointments[str(channel.id)] = {}

        channel_appointments = self.appointments.get(str(channel.id))
        channel_appointments[str(message.id)] = {"date_time": date_time.strftime(self.fmt), "reminder": reminder,
                                                 "title": title, "author_id": author_id, "recurring": recurring}

        self.save_appointments()

    def get_embed(self, title: str, date_time: datetime, reminder: int, recurring: int):
        embed = Embed(title="Neuer Termin hinzugefügt!",
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

        return embed

    @app_commands.command(name="list", description="Listet alle Termine dieses Channels auf")
    async def cmd_appointments(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=False)

        if str(interaction.channel.id) in self.appointments:
            channel_appointments = self.appointments.get(str(interaction.channel.id))
            answer = f'Termine dieses Channels:\n'
            delete = []

            for message_id, appointment in channel_appointments.items():
                try:
                    message = await interaction.channel.fetch_message(int(message_id))
                    answer += f'{appointment["date_time"]}: {appointment["title"]} => ' \
                              f'{message.jump_url}\n'
                except errors.NotFound:
                    delete.append(message_id)

            if len(delete) > 0:
                for key in delete:
                    channel_appointments.pop(key)
                self.save_appointments()

            await interaction.followup.send(answer, ephemeral=False)
        else:
            await interaction.followup.send("Für diesen Kanal existieren derzeit keine Termine.", ephemeral=True)

    async def handle_reactions(self, payload):
        channel = await self.bot.fetch_channel(payload.channel_id)
        channel_appointments = self.appointments.get(str(payload.channel_id))
        if channel_appointments:
            appointment = channel_appointments.get(str(payload.message_id))
            if appointment:
                if payload.user_id == appointment["author_id"]:
                    message = await channel.fetch_message(payload.message_id)
                    await message.delete()
                    channel_appointments.pop(str(payload.message_id))

        self.save_appointments()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.emoji.name in ["🗑️"]:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds) > 0 and message.embeds[0].title == "Neuer Termin hinzugefügt!":
                await self.handle_reactions(payload)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Appointments(bot))
