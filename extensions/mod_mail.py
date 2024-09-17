import io
from typing import List

import discord
from discord import Message, Guild
from discord.ext import commands

from views.mod_mail_view import ModMailView


class ModMail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author == self.bot.user:
            return

        if type(message.channel) is discord.DMChannel:
            guilds = await self.find_guilds(message.author)

            if len(guilds) == 1:
                await self.send_modmail(guilds[0], message)
            else:
                await message.channel.send(
                    "Um deine Nachricht an die Moderation des richtigen Server weiterleiten zu können musst du hier bitte den gewünschten Server auswählen.",
                    view=ModMailView(guilds, message, self.send_modmail))

    async def send_modmail(self, guild: Guild, orig_message: Message) -> None:
        channel_id = self.bot.get_settings(guild.id).modmail_channel_id
        channel = await self.bot.fetch_channel(channel_id)
        files = []

        for attachment in orig_message.attachments:
            fp = io.BytesIO()
            await attachment.save(fp)
            files.append(discord.File(fp, filename=attachment.filename))

        await channel.send(f"Support Nachricht von <@!{orig_message.author.id}>:")
        try:
            await channel.send(orig_message.content, files=files, stickers=orig_message.stickers)
        except discord.Forbidden:
            await channel.send(f"{orig_message.content}\n+ Sticker:\n{orig_message.stickers[0].url}", files=files)
        await orig_message.channel.send(f"Vielen Dank für deine Nachricht. Ich habe deine Nachricht an die Moderation "
                                        f"des Servers {guild.name} weitergeleitet. Es wird sich so schnell wie "
                                        f"möglich jemand bei dir melden.")

    async def find_guilds(self, user: discord.User) -> List[discord.Guild]:
        guilds = []

        for guild in self.bot.guilds:
            try:
                member = await guild.fetch_member(user.id)
                guilds.append(guild)
            except discord.errors.NotFound:
                pass

        return guilds


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModMail(bot))
