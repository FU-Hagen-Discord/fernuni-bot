import io
import os

import disnake
from disnake.ext import commands


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_SUPPORT_CHANNEL"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if type(message.channel) is disnake.DMChannel:
            channel = await self.bot.fetch_channel(self.channel_id)
            files = []

            for attachment in message.attachments:
                fp = io.BytesIO()
                await attachment.save(fp)
                files.append(disnake.File(fp, filename=attachment.filename))

            await channel.send(f"Support Nachricht von <@!{message.author.id}>:")
            await channel.send(message.content, files=files)
