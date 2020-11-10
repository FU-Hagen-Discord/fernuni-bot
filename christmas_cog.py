import os

from discord.ext import commands

import utils


class ChristmasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_ADVENT_CALENDAR_CHANNEL"))

    @commands.command("story")
    @commands.check(utils.is_mod)
    async def cmd_update_welcome(self, ctx, *args):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = f"Einreichung von <@!{ctx.author.id}>:\n"

        for arg in args:
            message += f"{arg} "

        await channel.send(message)
