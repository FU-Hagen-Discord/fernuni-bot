from discord.ext import commands

import os


class ChangeLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = os.getenv("DISCORD_CHANGE_LOG_CHANNEL")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        channel = await self.bot.fetch_channel(self.channel_id)
        await channel.send(f"Message edited by <@!{before.author.id}>:")
        await channel.send(before.content)
        pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        channel = await self.bot.fetch_channel(self.channel_id)
        await channel.send(f"Message edited by <@!{message.author.id}>:")
        await channel.send(message.content)
        pass