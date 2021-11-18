import asyncio
import json
import os
from datetime import datetime, timedelta

from disnake import ApplicationCommandInteraction, Member
from disnake.ext import commands, tasks
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


class Christmas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.seasonal_events_category = int(os.getenv("DISCORD_SEASONAL_EVENTS_CATEGORY"))
        self.advent_calendar_channel = int(os.getenv("DISCORD_ADVENT_CALENDAR_CHANNEL_2021"))
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

    @commands.slash_command(name="advent", guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_advent(self, interaction: ApplicationCommandInteraction):
        pass

    @cmd_advent.sub_command(name="assign", description="Einer Person ein Türchen zuweisen",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    @commands.check(utils.is_mod)
    async def cmd_advent_assign(self, interaction: ApplicationCommandInteraction, day: int, member: Member, name: str):
        if self.advent_calendar[day - 1]["assigned"]:
            await interaction.response.send_message("Das gewählte Türchen ist bereits vergeben.", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True)
            await self.assign_day(day, member, name)
            await interaction.edit_original_message(content="Das gewählte Türchen wurde vergeben.")

    @cmd_advent.sub_command(name="remaining", description="Noch nicht zugewiesene Türchen ausgeben lassen.",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    @commands.check(utils.is_mod)
    async def cmd_advent_remaining(self, interaction: ApplicationCommandInteraction):
        message = f"Noch verfügbare Türchen: "

        for day in self.advent_calendar:
            if not day["assigned"]:
                message += f"{day['number']}, "

        await interaction.response.send_message(message[:-2], ephemeral=True)

    async def assign_day(self, day: int, member: Member, name: str):
        category = await self.bot.fetch_channel(self.seasonal_events_category)
        channel = await category.create_text_channel(f"{day}-{name}")
        await channel.set_permissions(member, view_channel=True)
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
