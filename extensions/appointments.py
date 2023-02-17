import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import NewType, Union, Dict

from discord import app_commands, errors, Embed, Interaction, VoiceChannel, StageChannel, TextChannel, \
    ForumChannel, CategoryChannel, Thread, PartialMessageable
from discord.ext import tasks, commands

from views.appointment_view import AppointmentView

Channel = NewType('Channel', Union[
    VoiceChannel, StageChannel, TextChannel, ForumChannel, CategoryChannel, Thread, PartialMessageable, None])


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
                                                       channel_appointment["attendees"],
                                                       channel_appointment["ics_uuid"],
                                                       channel_appointment["description"],
                                                       channel_appointment["recurring"])
                        channel_appointments.pop(key)
        self.save_appointments()

    @timer.before_loop
    async def before_timer(self):
        await asyncio.sleep(60 - datetime.now().second)

    async def add_appointment(self, channel: Channel, author_id: int, date: str, time: str, reminder: int, title: str,
                              attendees: Dict, ics_uuid: str, description: str = "", recurring: int = None) -> None:
        try:
            date_time = datetime.strptime(f"{date} {time}", self.fmt)
        except ValueError:
            await channel.send("Fehler! Ungültiges Datums und/oder Zeit Format!")
            return

        message = await self.send_or_update_appointment(channel, author_id, description, title, date_time, reminder,
                                                        recurring, attendees)

        if str(channel.id) not in self.appointments:
            self.appointments[str(channel.id)] = {}

        channel_appointments = self.appointments.get(str(channel.id))
        channel_appointments[str(message.id)] = {"date_time": date_time.strftime(self.fmt), "reminder": reminder,
                                                 "title": title, "author_id": author_id, "recurring": recurring,
                                                 "description": description, "attendees": attendees,
                                                 "ics_uuid": ics_uuid}

        self.save_appointments()

    # /appointments add date:31.08.2022 time:20:00 reminder:60 title:Test
    @app_commands.command(name="add", description="Fügt dem Kanal einen neunen Termin hinzu.")
    @app_commands.describe(date="Tag des Termins (z. B. 21.10.2015).", time="Uhrzeit des Termins (z. B. 13:37).",
                           reminder="Wie viele Minuten bevor der Termin startet, soll eine Erinnerung verschickt werden?",
                           title="Titel des Termins.", description="Beschreibung des Termins.",
                           recurring="In welchem Intervall (in Tagen) soll der Termin wiederholt werden?")
    async def cmd_add_appointment(self, interaction: Interaction, date: str, time: str, reminder: int, title: str,
                                  description: str = "", recurring: int = None):

        await interaction.response.defer(ephemeral=True)
        attendees = {str(interaction.user.id): 1}
        await self.add_appointment(interaction.channel, interaction.user.id, date, time, reminder, title, attendees,
                                   str(uuid.uuid4()), description, recurring)
        await interaction.edit_original_response(content="Termin erfolgreich erstellt!")

    def get_embed(self, title: str, organizer: int, description: str, date_time: datetime, reminder: int,
                  recurring: int, attendees: Dict):
        embed = Embed(title=title,
                      description="Benutze die Buttons unter dieser Nachricht, um dich für Benachrichtigungen zu "
                                  "diesem Termin an- bzw. abzumelden.",
                      color=19607)

        embed.add_field(name="Erstellt von", value=f"<@{organizer}>", inline=False)
        if len(description) > 0:
            embed.add_field(name="Beschreibung", value=description, inline=False)
        embed.add_field(name="Startzeitpunkt", value=f"{date_time.strftime(self.fmt)}", inline=False)
        if reminder > 0:
            embed.add_field(name="Benachrichtigung", value=f"{reminder} Minuten vor dem Start", inline=False)
        if recurring:
            embed.add_field(name="Wiederholung", value=f"Alle {recurring} Tage", inline=False)
        embed.add_field(name=f"Teilnehmerinnen ({len(attendees)})",
                        value=",".join([f"<@{attendee}>" for attendee in attendees.keys()]))

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

    async def send_or_update_appointment(self, channel, organizer, description, title, date_time, reminder, recurring,
                                         attendees, message=None):
        embed = self.get_embed(title, organizer, description, date_time, reminder, recurring, attendees)
        if message:
            return await message.edit(embed=embed, view=AppointmentView(self))
        else:
            return await channel.send(embed=embed, view=AppointmentView(self))

    async def update_legacy_appointments(self):
        new_appointments = {}
        for channel_id, appointments in self.appointments.items():
            channel_appointments = {}
            try:
                channel = await self.bot.fetch_channel(int(channel_id))

                for message_id, appointment in appointments.items():
                    if appointment.get("attendees") is not None:
                        continue
                    try:
                        message = await channel.fetch_message(int(message_id))
                        title = appointment.get("title")
                        date_time = appointment.get("date_time")
                        reminder = appointment.get("reminder")
                        recurring = appointment.get("recurring")
                        author_id = appointment.get("author_id")
                        description = ""
                        attendees = {}
                        ics_uuid = str(uuid.uuid4())

                        for reaction in message.reactions:
                            if reaction.emoji == "👍":
                                async for user in reaction.users():
                                    if user.id != self.bot.user.id:
                                        attendees[str(user.id)] = 1

                        dt = datetime.strptime(f"{date_time}", self.fmt)
                        await self.send_or_update_appointment(channel, author_id, description, title, dt, reminder,
                                                              recurring, attendees, message=message)
                        channel_appointments[message_id] = {"date_time": date_time,
                                                            "reminder": reminder,
                                                            "title": title,
                                                            "author_id": author_id,
                                                            "recurring": recurring,
                                                            "description": description,
                                                            "attendees": attendees,
                                                            "ics_uuid": ics_uuid}

                    except:
                        pass
            except:
                pass

            if len(channel_appointments) > 0:
                new_appointments[channel_id] = channel_appointments

        self.appointments = new_appointments
        self.save_appointments()


async def setup(bot: commands.Bot) -> None:
    appointments = Appointments(bot)
    await bot.add_cog(appointments)
    bot.add_view(AppointmentView(appointments))
    await appointments.update_legacy_appointments()
