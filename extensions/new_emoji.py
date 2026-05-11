import os
import random

from discord import Emoji, Guild
from discord.ext import commands

"""
  Umgebungsvariablen:
  DISCORD_KAFFEEECKE_ID - Channel ID der Kaffeeecke
  DISCORD_GUILD - Guild ID des Servers
"""

class New_emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.kaffeeecke_id = os.getenv('DISCORD_KAFFEEECKE_ID')
        self.guild_id = os.getenv('DISCORD_GUILD')

    #Listener if new emoji is created
    @commands.Cog.listener()
    async def on_guild_emojis_update(guild: discord.Guild, before: Sequence[discord.Emoji], after: Sequence[discord.Emoji]) -> None:
        if guild.id != self.guild_id:
            return

        #IDs of Emojis before and after
        before_ids = {e.id for e in before}
        after_ids  = {e.id for e in after}

        #Get the emojis added and removed
        added   = [e for e in after  if e.id not in before_ids]
        removed = [e for e in before if e.id not in after_ids]

        # Falls added nicht leer
        if added:
            await kaffeeecke = self.bot.fetch_channel(int(self.kaffeeecke_id))
            for emoji in added:
                await kaffeeecke.send(f"Es gibt ein neues Emoji :{emoji.mention}:)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
