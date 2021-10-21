import os

import disnake
from disnake.ext import commands

import utils
from cogs.help import help, handle_error


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_WELCOME_CHANNEL", "0"))
        self.message_id = int(os.getenv("DISCORD_WELCOME_MSG", "0"))

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

        embed = disnake.Embed(title="Herzlich Willkommen auf dem Discord von Studierenden für Studierende.",
                              description="Disclaimer: Das hier ist kein offizieller Kanal der Fernuni. Hier findet auch keine offizielle Betreuung durch die Fernuni statt. Dieser Discord dient zum Austausch unter Studierenden über einzelne Kurse, um sich gegenseitig helfen zu können, aber auch um über andere Themen in einen Austausch zu treten. Es soll KEIN Ersatz für die Kanäle der Lehrgebiete sein, wie die Newsgroups, Moodle-Foren und was es noch so gibt. Der Discord soll die Möglichkeit bieten, feste Lerngruppen zu finden und sich in diesen gegenseitig zu helfen und zu treffen. Zudem soll er durch den Austausch in den Kanälen auch eine Art flexible Lerngruppe zu einzelnen Kursen ermöglichen. Daher ist unser Apell an euch: Nutzt bitte auch die Betreuungsangebote der entsprechenden Kurse, in die ihr eingeschrieben seid. ")
        #kürzen
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/avatars/697842294279241749/c7d3063f39d33862e9b950f72ab71165.webp")
               
        embed.add_field(name="Boty McBotface",
                        value=f"Boty ist der Server-Bot und kann dein Freund und Helfer sein, wenn es um die Organisation deines Studiums geht. In <#{os.getenv('DISCORD_BOTUEBUNGSPLATZ_CHANNEL')}> kann man mit den verschiedenen Befehlen rumprobieren, bei `!help` wird er dir per Direktnachricht einen Überblick von seinen Funktionen geben.", 
                        #channelverlinkung anders?
                        inline=False)

        embed.add_field(name="Vorstellung",
                        value=f"Es gibt einen <#{os.getenv('DISCORD_VORSTELLUNGSCHANNEL')}>. Wir würden uns freuen, wenn ihr euch kurz vorstellen würdet. So ist es möglich, Gemeinsamkeiten zu entdecken und man weiß ungefähr, mit wem man es zu tun hat. Hier soll auch gar nicht der komplette Lebenslauf stehen, schreibt einfach das, was ihr so über euch mitteilen möchtet.",
                        inline=False)
                
        embed.add_field(name="Rollen",
                        value=f"Es gibt verschiedene Rollen hier. Derzeit sind das zum einen Rollen zu den verschiedenen Studiengängen unserer Fakultät (sowie allgemeinere Rollen), Farbrollen. Wirf doch mal einen Blick in <#{os.getenv('DISCORD_ROLLEN_CHANNEL')}>",
                        inline=False)
        
        embed.add_field(name="Lerngruppen",
                        value="Wenn ihr eine feste Lerngruppe gründen möchtet, dann könnt ihr dafür gerne einen eigenen Textchannel bekommen. Sagt einfach bescheid, dann kann dieser erstellt werden. Ihr könnt dann auch entscheiden, ob nur ihr Zugang zu diesem Channel haben möchtet, oder ob dieser für alle zugänglich sein soll.",
                        inline=False)

        embed.add_field(name="Nachrichten anpinnen",
                        value="Wenn ihr Nachrichten in einem Channel anpinnen möchtet, könnt ihr dafür unseren Bot verwenden. Setzt einfach eine :pushpin: Reaktion auf die entsprechende Nachricht und der pin-bot erledigt den Rest.", 
                        #eventuell bei Boty ansiedeln
                        inline=False)    
                
        embed.add_field(name="Regeln",
                        value="Es gibt hier ein paar, wenige Regeln, an die wir uns alle halten wollen. Diese findet ihr hier https://discordapp.com/channels/353315134678106113/697729059173433344/709475694157234198",
                        inline=False)
        
        embed.add_field(name="Discord Tipps",
                        value="Mit `Strg` + `#` (deutscher Tastaturlayout) erhält man einen Überblick über die Discord-Shortcuts. \n- Zur Übersichtlichkeit kann man stummgeschaltete Channels ausblenden: https://support.discord.com/hc/de/articles/213599277-Wie-verstecke-Ich-stumme-Kanäle-,\n- Markdown (und damit Code-Blöcke) gibt es hier auch: https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-",
                        inline=False)   

        await message.edit(content="", embed=embed)

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
