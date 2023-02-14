import io
import os

import discord
from discord.ext import commands


class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_SUPPORT_CHANNEL"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if type(message.channel) is discord.DMChannel:
            channel = await self.bot.fetch_channel(self.channel_id)
            files = []

            for attachment in message.attachments:
                fp = io.BytesIO()
                await attachment.save(fp)
                files.append(discord.File(fp, filename=attachment.filename))

            await channel.send(f"Support Nachricht von <@!{message.author.id}>:")
            await channel.send(message.content, files=files)
            await message.channel.send("Vielen Dank für deine Nachricht. Ich habe deine Nachricht an das Mod-Team "
                                       "weitergeleitet. Falls dir dich mit einer Frage oder einem Problem an mich "
                                       "gewandt hast, wird sich so schnell wie möglich jemand bei dir melden.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModMail(bot))
