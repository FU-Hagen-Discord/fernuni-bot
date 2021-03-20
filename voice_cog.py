import discord
from discord.ext import commands

import utils


class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="voice")
    @commands.check(utils.is_mod)
    async def cmd_voice(self, ctx, switch):
        voice_channels = ctx.guild.voice_channels
        print(voice_channels[0].user_limit)
        if switch == "open":
            for voice_channel in voice_channels:
                await voice_channel.edit(user_limit=0)
        elif switch == "close":
            for voice_channel in voice_channels:
                await voice_channel.edit(user_limit=1)
