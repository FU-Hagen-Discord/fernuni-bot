import os
import random

from discord import Member
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        if (before.pending != after.pending and not after.pending) or self.bot.is_dev_mode_activated():
            await self.send_welcome_message(before)

    async def send_welcome_message(self, before):
        channel_id = self.bot.get_settings(before.guild.id).greeting_channel_id
        channel = await self.bot.fetch_channel(channel_id)

        welcome_message = f"""
        Hey {before.mention}, 
schön, dass du hergefunden hast :nerd: 

Unsere Serverregeln findest du hier: <#{os.getenv('DISCORD_RULE_CHANNEL')}> 
Antworten auf häufig gestellte Fragen findest du hier: <#{os.getenv('DISCORD_FAQ_CHANNEL')}>
Weitere Informationen zu den Funktionen des Servers und des Bots findest du hier: <#{os.getenv('DISCORD_BOT_MANUAL_CHANNEL')}>
Zur Lerngruppen-Suche geht es hier lang: <#{os.getenv('DISCORD_LEARNINGGROUPS_POST')}> 
Quatschen kannst du hier: ⁠<#{os.getenv('DISCORD_CHATTING_CHANNEL_1')}> oder ⁠<#{os.getenv('DISCORD_CHATTING_CHANNEL_2')}> 
Stelle gerne Fragen an die Admins/Moderation/den Bot per DM oder einfach hier: <#{os.getenv('DISCORD_QUESTIONS_AND_ANSWERS_CHANNEL')}>       
        """

        await channel.send(welcome_message)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
