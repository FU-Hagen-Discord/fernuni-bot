import asyncio
import datetime
import json
import re

import discord
from discord.ext import tasks, commands


class AppointmentsCog(commands.Cog):
    def __init__(self, bot, fmt, APPOINTMENTS_FILE):
        self.bot = bot
        self.fmt = fmt
        self.timer.start()
        self.appointments = {}
        self.app_file = APPOINTMENTS_FILE
        self.load_appointments()

    def cog_unload(self):
        print("unload")
        self.timer.cancel()

    def load_appointments(self):
        """ Loads all appointments from APPOINTMENTS_FILE """

        appointments_file = open(self.app_file, mode='r')
        self.appointments = json.load(appointments_file)

    @tasks.loop(minutes=1)
    async def timer(self):
        delete = []

        for channel_id, channel_appointments in self.appointments.items():
            for message_id, appointment in channel_appointments.items():
                now = datetime.datetime.now()
                date_time = datetime.datetime.strptime(appointment[0], self.fmt)
                remind_at = date_time - datetime.timedelta(minutes=appointment[1])

                if now >= remind_at:
                    try:
                        channel = await self.bot.fetch_channel(int(channel_id))
                        message = await channel.fetch_message(int(message_id))
                        reactions = message.reactions
                        diff = int(round(((date_time - now).total_seconds() / 60), 0))
                        answer = f"Benachrichtigung!\nDer Termin \"{appointment[2]}\" ist "

                        if appointment[1] > 0 and diff > 0:
                            answer += f"in {diff} Minuten fällig."
                            appointment[1] = 0
                        else:
                            answer += f"jetzt fällig. :loudspeaker: "
                            delete.append(message_id)

                        answer += f"\n"
                        for reaction in reactions:
                            if reaction.emoji == "👍":
                                async for user in reaction.users():
                                    if user != self.bot.user:
                                        answer += f"<@!{str(user.id)}>"

                        await channel.send(answer)

                        if str(message.id) in delete:
                            await message.delete()
                    except discord.errors.NotFound:
                        delete.append(message_id)

            if len(delete) > 0:
                for key in delete:
                    channel_appointments.pop(key)
                self.save_appointments()

    @timer.before_loop
    async def before_timer(self):
        await asyncio.sleep(60 - datetime.datetime.now().second)

    @commands.command(name="add-appointment")
    async def cmd_add_appointment(self, ctx, date, time, reminder, title):
        """ Add appointment to a channel """

        channel = ctx.channel
        try:
            date_time = datetime.datetime.strptime(f"{date} {time}", self.fmt)
        except ValueError:
            await ctx.send("Fehler! Ungültiges Datums und/oder Zeit Format!")
            return

        if not re.match(r"^\d+$", reminder):
            await ctx.send("Fehler! Benachrichtigung muss eine positive ganze Zahl (in Minuten) sein!")
            return

        embed = discord.Embed(title="Neuer Termin hinzugefügt!",
                              description=f"Wenn du eine Benachrichtigung zum Beginn des Termins, sowie {reminder} "
                                          f"Minuten vorher erhalten möchtest, reagiere mit :thumbsup: auf diese Nachricht.",
                              color=19607)

        embed.add_field(name="Titel", value=title, inline=False)
        embed.add_field(name="Startzeitpunkt", value=f"{date} {time}", inline=False)
        embed.add_field(name="Benachrichtigung", value=f"{reminder} Minuten vor dem Start", inline=False)

        message = await ctx.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")

        if str(channel.id) not in self.appointments:
            self.appointments[str(channel.id)] = {}

        channel_appointments = self.appointments.get(str(channel.id))
        channel_appointments[str(message.id)] = [date_time.strftime(self.fmt), int(reminder), title,
                                                 ctx.author.id]

        self.save_appointments()

    @commands.command(name="appointments")
    async def cmd_appointments(self, ctx):
        """ List (and link) all Appointments in the current channel """

        if str(ctx.channel.id) in self.appointments:
            channel_appointments = self.appointments.get(str(ctx.channel.id))
            answer = f'Termine dieses Channels:\n'
            delete = []

            for message_id, appointment in channel_appointments.items():
                try:
                    message = await ctx.channel.fetch_message(int(message_id))
                    answer += f'{appointment[0]}: {appointment[2]} => ' \
                              f'{message.jump_url}\n'
                except discord.errors.NotFound:
                    delete.append(message_id)

            if len(delete) > 0:
                for key in delete:
                    channel_appointments.pop(key)
                self.save_appointments()

            await ctx.channel.send(answer)
        else:
            await ctx.send("Für diesen Channel existieren derzeit keine Termine")

    def add_appointment(self, channel):
        pass

    def save_appointments(self):
        appointments_file = open(self.app_file, mode='w')
        json.dump(self.appointments, appointments_file)

    async def handle_reactions(self, payload):
        channel = await self.bot.fetch_channel(payload.channel_id)
        channel_appointments = self.appointments.get(str(payload.channel_id))
        if channel_appointments:
            appointment = channel_appointments.get(str(payload.message_id))
            if appointment:
                if payload.user_id == appointment[3]:
                    message = await channel.fetch_message(payload.message_id)
                    await message.delete()
                    channel_appointments.pop(str(payload.message_id))

        self.save_appointments()
