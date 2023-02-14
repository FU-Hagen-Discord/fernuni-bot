import os
import random

from discord.ext import commands

import utils


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_WELCOME_CHANNEL", "0"))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await utils.send_dm(member,
                            f"Herzlich Willkommen auf diesem Discord-Server. Wir hoffen sehr, dass du dich hier wohl fühlst. Alle notwendigen Informationen, die du für den Einstieg brauchst, findest du in <#{self.channel_id}>\n"
                            f"Wir würden uns sehr freuen, wenn du dich in <#{os.getenv('DISCORD_VORSTELLUNGSCHANNEL')}> allen kurz vorstellen würdest. Es gibt nicht viele Regeln zu beachten, doch die Regeln, die aufgestellt sind, findest du hier:  https://discordapp.com/channels/353315134678106113/697729059173433344/709475694157234198 .\n"
                            f"Du darfst dir außerdem gerne im Channel <#{os.getenv('DISCORD_ROLLEN_CHANNEL')}> die passende Rolle zu den Studiengängen in denen du eingeschrieben bist zuweisen. \n\n"
                            f"Abschließend bleibt mir nur noch, dir hier viel Spaß zu wünschen, und falls du bei etwas hilfe brauchen solltest, schreib mir doch eine private Nachricht, das Moderatoren Team wird sich dann darum kümmern.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.pending != after.pending and not after.pending:
            channel = await self.bot.fetch_channel(self.channel_id)
            welcome_messages = [
                f"Willkommen {before.mention} auf dem Discordserver von und für Studis der Fakultät für Mathematik und Informatik der FernUni! :partying_face:",
                f"Hi {before.mention}, herzlich willkommen! :hugging: ",
                f"Hey {before.mention}, hast du Kuchen mitgebracht? :cake:",
                f"Hey {before.mention} ist da! :partying_face:",
                f"Guten Tag, {before.mention}, und herzlich Willkommen! :partying_face:",
                f"Hi {before.mention}, dein Serverprofil sieht noch ein wenig leer aus - nicht wahr? Im "
                f"<#{os.getenv('DISCORD_ROLLEN_CHANNEL')}> kannst du dir Studiengangs- und/ oder Spezial-Rollen "
                f"vergeben und die entsprechenden Channels freischalten :wink:",
                f"Hi {before.mention}, bei dem Channel <#{os.getenv('DISCORD_ROLLEN_CHANNEL')}> kannst du dir Studiengangs- "
                f"und/ oder Spezial-Rollen vergeben lassen :blush:",
                f" Moin {before.mention}, in <#{os.getenv('DISCORD_DISCORDFAQ_CHANNEL')}>  wurden nützliche Infos zu der "
                f"Plattform Discord gesammelt. :notepad_spiral: Schau gerne vorbei!",
                f" Willkommen, {before.mention}! Beim <#{os.getenv('DISCORD_SERVERFAQ_CHANNEL')}> wurden nützliche Infos zu diesem "
                f"Server gesammelt. Schau sie dir gerne an :notepad_spiral:",
                f"Willkommen {before.mention}, hast du die <#{os.getenv('DISCORD_OFFTOPIC_CHANNEL')}> schon "
                f"entdeckt? :coffee: Dort kann man über alles reden, was nicht studienspezifisch ist - #offtopic 😊. ",
                f":wave: {before.mention}, erzähl gerne etwas über dich in <#{os.getenv('DISCORD_VORSTELLUNGSCHANNEL')}>.",
                f"Hallo {before.mention}! Mach es dir gemütlich und zögere nicht, mir per privaten Nachricht Fragen"
                f" zu stellen, wenn du Hilfe vom Mod-Team brauchst :love_letter:",
                f"Hallo {before.mention}, hast du Cookies mitgebracht? :cake:",
                f"Hey {before.mention}! Im Channel <#{os.getenv('DISCORD_UNITALK_CHANNEL')}> kannst du dich mit "
                f"Kommilitoninnen über Themen rund um das Studium unterhalten :student: "
            ]
        await channel.send(msg=random.choice(welcome_messages))

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
