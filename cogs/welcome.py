import os

import discord
from discord.ext import commands

import utils
from cogs.help import help, handle_error


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_FAQ_CHANNEL"))
        self.message_id = int(os.getenv("DISCORD_WELCOME_MSG"))

    @help(
      category="updater",
      brief="aktualisiert die Willkommensnachricht.",
      mod=True
      )
    @commands.command("update-welcome")
    @commands.check(utils.is_mod)
    async def cmd_update_welcome(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.message_id)

    """
    #🖼 FAQ    
    """

        embed = discord.Embed(title="Inhaltsverzeichnis ",
                              description="Frequently Asked Questions")       
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/avatars/697842294279241749/c7d3063f39d33862e9b950f72ab71165.webp")
         
        #Ist ein leerer Feldname zulässig?
        embed.add_field(name="", 
                        value=f"[1. Boty McBotface](Link zur Nachricht) \n"
                                "[2. Lerngruppen](Link) \n"
                                "[3. Rollen](Link) \n"
                                "[4. Fun & Games] (Link) \n"
                                "[5.FernUni 101](Link) \n"
                                "[6. Discord 101](Link) \n", 
                        inline=False)  

        await message.edit(content="", embed=embed)
#TODO: Damit die einzelne Links auf exitierende Nachrichten zeigen, müsste man den Inhaltsverzeichnis separat (nachträglich) aktualisieren können.

        """
        ##🖼 Boty McBotface 
        """

        """
        ##🖼 Lerngruppen 
        """

        """
        ##🖼 Rollen 
        """

        """
        ##🖼 Fun & Games 
        """

        """
        ##🖼 FernUni 101 
        """

        """
        ##🖼 Discord 101
        """


    """
    #🖼 Server    
    """

        """
        ##🖼 Regeln
        """



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
            channel = await self.bot.fetch_channel(int(os.getenv("DISCORD_GREETING_CHANNEL")))
            await channel.send(f"Herzlich Willkommen <@!{before.id}> im Kreise der Studentinnen :wave:")

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
