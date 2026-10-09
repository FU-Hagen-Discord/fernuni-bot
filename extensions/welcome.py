import os
import random

from discord import Member, Message, MessageType
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def on_message(self, message: Message) -> None:
        """ Greets new members. Since member events require the privileged members intent, the join system message,
        that Discord posts in the system channel of the guild, is used instead. """

        if message.type != MessageType.new_member or message.guild is None or message.author.bot:
            return

        channel_id = self.bot.get_settings(message.guild.id).greeting_channel_id
        channel = await self.bot.fetch_channel(channel_id)
        await channel.send(random.choice(self.welcome_messages(message.author)))

    @staticmethod
    def welcome_messages(member: Member) -> list[str]:
            return [
                f"Willkommen {member.mention} auf dem Discordserver von und für Studis der Fakultät für Mathematik und Informatik der FernUni! :partying_face:",
                f"Hi {member.mention}, herzlich willkommen! :hugging: ",
                f"Guten Tag, {member.mention}, und herzlich Willkommen! :partying_face:",
                f"Hi {member.mention}, in <id:customize> kannst du dir Studiengangs- und Spezial-Rollen vergeben und damit u.a. die Standardsichtbarkeit von Modulkanälen für dich ändern :wink:",
                f"Hi {member.mention}, in <id:customize> kannst du dir Studiengangs- und Spezial-Rollen zuweisen :blush:",
                f"Willkommen, {member.mention}! In <#{os.getenv('DISCORD_SERVERFAQ_CHANNEL')}> wurden nützliche Infos zu diesem Server gesammelt. Schau sie dir gerne an :notepad_spiral:",
                f"Willkommen {member.mention}, hast du die <#{os.getenv('DISCORD_OFFTOPIC_CHANNEL')}> schon entdeckt? :coffee: Dort kann man über alles reden, was nicht studiumspezifisch ist 😊",
                f":wave: {member.mention}, erzähl gerne etwas über dich in der <#{os.getenv('DISCORD_VORSTELLUNGSCHANNEL')}>.",
                f"Hallo {member.mention}! Mach es dir gemütlich und zögere nicht, mir per privater Nachricht Fragen zu stellen, wenn du Hilfe vom Mod-Team brauchst :love_letter:",
                f"Hey {member.mention}! In <#{os.getenv('DISCORD_UNITALK_CHANNEL')}> kannst du dich mit Kommilitoninnen über Themen rund um das Studium unterhalten :student: ",
                f"Herzlich willkommen {member.mention}! Wenn du Lust hast, dich mit anderen zusammen zu tun und dafür das Bot-Lerngruppensystem zu nutzen: schau im <#{os.getenv('DISCORD_LEARNINGGROUPS_INFO')}>-Kanal, wie der Beitritt und/oder die Gründung funktionieren!",
                f"Herzlich Willkommen, {member.mention} <:winking_boty:873222361015545906>",
                f"Hallo {member.mention}!"
            ]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
