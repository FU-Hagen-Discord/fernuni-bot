import json
import os
from datetime import datetime

from discord.ext import commands

import utils


class ChristmasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_ADVENT_CALENDAR_CHANNEL"))
        self.advent_calendar = []
        self.load_advent_calendar()

    def load_advent_calendar(self):
        advent_calendar_file = open("advent_calendar.json", mode='r')
        self.advent_calendar = json.load(advent_calendar_file)

    @commands.command("story")
    async def cmd_update_welcome(self, ctx, *args):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = f"Einreichung von <@!{ctx.author.id}>:\n"

        for arg in args:
            message += f"{arg} "

        await channel.send(message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == int(os.getenv("DISCORD_ADVENT_CALENDAR_MESSAGE")):
            roles = {}
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await guild.fetch_member(payload.user_id)
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.clear_reactions()

            for role in guild.roles:
                roles[str(role.id)] = role

            today = datetime.now()
            day = today.day if today.day <= 24 else 24

            if today < datetime(year=2020, month=12, day=1):
                return

            for i in range(0, day):
                door = self.advent_calendar[i]
                if payload.emoji.name == door["emote"]:
                    await member.add_roles(roles[door["role"]])
                    await utils.send_dm(member, f"Glückwunsch, du hast gerade {door['name']} geöffnet")
