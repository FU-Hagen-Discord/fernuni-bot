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

#Neue Nachricht
        """
        ##🖼 Regeln
        
            Es sind vier Regeln, die unbedingt einzuhalten sind: 
```md
1. Behandle alle mit Respekt. Keine diskriminierenden Äußerungen. Keine Belästigung.
2. Unterlasse das Einstellen von Werbung und Mehrfachpostings.
3. Betrüge nicht bei Prüfungsleistungen. Aufruf und Versuch werden mit einem Ban geahndet.
4. Teile oder erfrage keine Dateien, welche urheberrechtlich geschützt sind.
```
:mag: Link vom BMBF zur Orientierung in Sachen Urheberrecht: https://www.bmbf.de/de/was-forschende-und-lehrende-wissen-sollten-9523.html

:bulb: Ein Verstoß kann durch eine ernst gemeinte Entschuldigung wieder gut gemacht werden. 
```md
1. Bei Verstößen wird zunächst darauf hingewiesen. Sollte es danach weiterhin zu einem Regelverstoß kommen, so wird eine Verwarnung ausgesprochen.
2. Sollte die ausgesprochene Verwarnung keine Besserung bringen, so ist die nächste Maßnahme ein Kick von diesem Server. 
3. Bei weiteren Regelverstößen bleibt, als letzte und hoffentlich nicht notwendige Maßnahme, nur der Bann von diesem Server.
```
        """

#Neue Nachricht
        """
        ##🖼 Boty McBotface
        """
    
#Neue Nachricht
        """
        ##🖼 Lerngruppen
        """
        
#Neue Nachricht
        """
        ##🖼 Rollen 
        """

#Neue Nachricht
        """
        ##🖼 Fun & Games 
        """
        
#Neue Nachricht
        """
        ##🖼 FernUni 101 
        """

#Neue Nachricht
        """
        ##🖼 Discord 101
        """

#Neue Nachricht
    """
    #🖼 Server    
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
