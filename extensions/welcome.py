import os
import random

from discord import Member
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        if before.pending != after.pending and not after.pending:
            channel_id = self.bot.get_settings(before.guild.id).greeting_channel_id
            channel = await self.bot.fetch_channel(channel_id)
            welcome_messages = [
                f"Willkommen {before.mention} auf dem Discordserver von und für Studis der Fakultät für Mathematik und Informatik der FernUni! :partying_face:",
                f"Hi {before.mention}, herzlich willkommen! :hugging: ",
                f"Guten Tag, {before.mention}, und herzlich Willkommen! :partying_face:",
                f"Hi {before.mention}, bei <id:customize> kannst du dir Studiengangs- und/ oder Spezial-Rollen "
                f"vergeben und damit u.a. die Standartsichtbarkeit von Kurschannels für dich ändern :wink:",
                f"Hi {before.mention}, bei <id:customize> kannst du dir Studiengangs- und/ oder Spezial-Rollen "
                f"vergeben lassen :blush:",
                f" Moin {before.mention}, in <#{os.getenv('DISCORD_DISCORDFAQ_CHANNEL')}>  wurden nützliche Infos zu der "
                f"Plattform Discord gesammelt. :notepad_spiral: Schau gerne vorbei!",
                f" Willkommen, {before.mention}! Beim <#{os.getenv('DISCORD_SERVERFAQ_CHANNEL')}> wurden nützliche Infos zu diesem "
                f"Server gesammelt. Schau sie dir gerne an :notepad_spiral:",
                f"Willkommen {before.mention}, hast du die <#{os.getenv('DISCORD_OFFTOPIC_CHANNEL')}> schon "
                f"entdeckt? :coffee: Dort kann man über alles reden, was nicht studienspezifisch ist 😊",
                f":wave: {before.mention}, erzähl gerne etwas über dich in <#{os.getenv('DISCORD_VORSTELLUNGSCHANNEL')}>.",
                f"Hallo {before.mention}! Mach es dir gemütlich und zögere nicht, mir per privaten Nachricht Fragen"
                f" zu stellen, wenn du Hilfe vom Mod-Team brauchst :love_letter:",
                f"Hey {before.mention}! Im Channel <#{os.getenv('DISCORD_UNITALK_CHANNEL')}> kannst du dich mit "
                f"Kommilitoninnen über Themen rund um das Studium unterhalten :student: ",
                f"Herzlich willkommen {before.mention}! Wenn du Lust hast, dich mit anderen zusammen zu tun "
                f"und dafür das Bot-Lerngruppensystem zu nutzen: schau beim <#{os.getenv('DISCORD_LEARNINGGROUPS_INFO')}>"
                f"-Kanal, wie der Beitritt und / oder die Gründung funktionieren!"
            ]
            await channel.send(msg=random.choice(welcome_messages))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
