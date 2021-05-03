import discord
from discord.ext import commands

import utils
from help.help import help, handle_error


class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @help(
      brief="öffnet und schließt die Voice Kanäle",
      parameters={
        "switch": "`open` öffnet die Voice Kanäle. `close` schließt die Voice Kanäle."
      },
      mod=True
      )
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

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
