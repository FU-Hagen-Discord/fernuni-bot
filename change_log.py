from discord.ext import commands

import os


class ChangeLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = os.getenv("DISCORD_CHANGE_LOG_CHANNEL")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.bot.user == before.author:
            return

        channel = await self.bot.fetch_channel(self.channel_id)
        await channel.send(f"Message edited by <@!{before.author.id}>:")
        msg = await channel.send(before.content)
        await msg.delete()

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if self.bot.user == message.author:
            return

        channel = await self.bot.fetch_channel(self.channel_id)
        await channel.send(f"Message deleted by <@!{message.author.id}>:")
        await channel.send(message.content)
