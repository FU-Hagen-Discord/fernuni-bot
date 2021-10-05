from disnake.ext import commands

import utils
from cogs.help import help, handle_error


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @help(
      brief="Öffnet und schließt die Voice-Kanäle.",
      parameters={
        "switch": "open öffnet die Voice-Kanäle, close schließt die Voice-Kanäle."
      },
      example="!voice close",
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
