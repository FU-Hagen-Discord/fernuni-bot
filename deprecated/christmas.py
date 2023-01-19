import asyncio
import json
import os
from datetime import datetime, timedelta

from discord import Interaction, Member, app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import utils

load_dotenv()


def create_advent_calendar():
    advent_calendar = []
    startdate = utils.date_from_string(os.getenv("DISCORD_ADVENT_CALENDAR_START")).astimezone()

    for i in range(0, 24):
        advent_calendar.append({
            "number": i + 1,
            "date": utils.date_to_string(startdate + timedelta(days=i)),
            "assigned": False,
            "opened": False
        })

    return advent_calendar


@app_commands.guild_only()
class Christmas(commands.GroupCog, name="advent"):
    def __init__(self, bot):
        self.bot = bot
        self.seasonal_events_category = int(os.getenv("DISCORD_SEASONAL_EVENTS_CATEGORY"))
        self.advent_calendar_channel = int(os.getenv("DISCORD_ADVENT_CALENDAR_CHANNEL_2022"))
        self.file_name = os.getenv("DISCORD_ADVENT_CALENDAR_FILE")
        self.advent_calendar = self.load()
        self.advent_calendar_loop.start()

    def load(self):
        with open(self.file_name, mode='r') as f:
            advent_calendar = json.load(f)

        if len(advent_calendar) == 0:
            advent_calendar = create_advent_calendar()

        return advent_calendar

    def save(self):
        with open(self.file_name, mode='w') as f:
            json.dump(self.advent_calendar, f)

    @app_commands.command(name="list", description="Erhalte die Liste aller Türchen mit Zuordnung und Thema")
    @app_commands.check(utils.is_mod)
    async def cmd_advent_list(self, interaction: Interaction):
        message = f"__**Adventskalender 2021**__\n\n"
        await interaction.response.defer(ephemeral=True)
        for day in self.advent_calendar:
            message += f"{day['number']}. "
            if day["assigned"]:
                message += f"<@!{day['assignee']}>: \"{day['name']}\""
            else:
                message += f"noch nicht zugewiesen"

            message += "\n"

        await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="assign", description="Einer Person ein Türchen zuweisen")
    @app_commands.describe(day="Adventstag des Türchens", member="User der das Türchen bespielt", name="Kanalname")
    @app_commands.guild_only()
    @app_commands.check(utils.is_mod)
    async def cmd_advent_assign(self, interaction: Interaction, day: int, member: Member, name: str):
        if "assigned" in self.advent_calendar[day - 1] and self.advent_calendar[day - 1]["assigned"]:
            await interaction.response.send("Das gewählte Türchen ist bereits vergeben. \n"
                                                    "Wenn du das Türchen an jemand anderen vergeben möchtest, oder das "
                                                    "Thema ändern möchtest, verwende `/advent reassign`.",
                                                    ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True)
            await self.assign_day(day, member, name)
            await interaction.followup.send(content="Das gewählte Türchen wurde vergeben.")

    @app_commands.command(name="reassign", description="Ein Türchen neu zuweisen")
    @app_commands.describe(day="Adventstag des Türchens", member="User der das Türchen bespielt", name="Kanalname")
    @app_commands.guild_only()
    @commands.check(utils.is_mod)
    async def cmd_advent_reassign(self, interaction: Interaction, day: int, member: Member,
                                  name: str):
        if not self.advent_calendar[day - 1]["assigned"]:
            await interaction.response.send("Das gewählte Türchen ist noch nicht vergeben. \n"
                                                    "Bitte verwende `/advent assign` um das Türchen an "
                                                    "jemanden zu vergeben.", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True)
            channel = await self.bot.fetch_channel(self.advent_calendar[day - 1]["channel"])
            old_member = await self.bot.fetch_user(self.advent_calendar[day - 1]["assignee"])
            await channel.set_permissions(old_member, overwrite=None)
            await self.assign_day(day, member, name)
            await interaction.followup.send(content="Das gewählte Türchen wurde neu vergeben.")

    @app_commands.command(name="remaining", description="Noch nicht zugewiesene Türchen ausgeben lassen.")
    @app_commands.guild_only()
    @commands.check(utils.is_mod)
    async def cmd_advent_remaining(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        message = f"Noch verfügbare Türchen: "

        for day in self.advent_calendar:
            if not day["assigned"]:
                message += f"{day['number']}, "

        await interaction.followup.send(message[:-2], ephemeral=True)

    async def assign_day(self, day: int, member: Member, name: str):
        category = await self.bot.fetch_channel(self.seasonal_events_category)
        channel = await category.create_text_channel(f"{day}-{name}")
        await channel.set_permissions(member.roles[0], view_channel=False)
        await channel.set_permissions(member, view_channel=True)
        await channel.send(f"Vielen Dank {member.mention}, dass du für das {day}. Türchen etwas zum Thema {name} "
                           f"vorbereiten möchtest. Dieser Channel ist für dich gedacht. Du kannst hier deinen Beitrag "
                           f"vorbereiten.\n\n"
                           f"Am {day}.12.2021 um 00:00 werden alle Nachrichten von dir, die in diesem Channel bis "
                           f"dahin geschrieben wurden, in einen eigenen Thread für diesen Tag übernommen.\n\n"
                           f"Beachte bitte, dass Sticker nicht verwendet werden können. Das gleiche gilt für Emojis, "
                           f"die nicht von diesem Server sind.\n\n"
                           f"Das Mod-Team wünscht dir viel Spaß bei der Vorbereitung.")
        self.advent_calendar[day - 1]["channel"] = channel.id
        self.advent_calendar[day - 1]["assigned"] = True
        self.advent_calendar[day - 1]["assignee"] = member.id
        self.advent_calendar[day - 1]["name"] = name
        self.save()

    async def open(self, day):
        source_channel = await self.bot.fetch_channel(day["channel"])
        assignee = await self.bot.fetch_user(day["assignee"])
        target_channel = await self.bot.fetch_channel(self.advent_calendar_channel)
        thread_name = f"{day['number']}. {day['name']}"

        message = await target_channel.send(f"{day['number']}. \"{day['name']}\", ein Beitrag von {assignee.mention}:")
        thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)
        day["thread"] = thread.id
        day["opened"] = True

        async for msg in source_channel.history(limit=None, oldest_first=True):
            if msg.author == assignee:
                if len(msg.stickers) > 0:
                    continue
                files = await utils.files_from_attachments(msg.attachments)
                await thread.send(content=msg.content, embeds=msg.embeds, files=files)

        await thread.send("--------------------------\nBeginn der Diskussion\n--------------------------")

        self.save()

    @tasks.loop(seconds=10)
    async def advent_calendar_loop(self):
        now = datetime.now()
        for day in self.advent_calendar:
            if not day["opened"]:
                due_date = utils.date_from_string(day["date"])
                if due_date <= now:
                    await self.open(day)
                else:
                    return

    @advent_calendar_loop.before_loop
    async def before_advent_calendar_loop(self):
        await asyncio.sleep(10 - datetime.now().second % 10)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Christmas(bot))
