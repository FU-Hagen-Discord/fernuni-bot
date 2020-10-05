import os

import discord
from discord.ext import commands

import utils


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 731078162334875689
        self.message_id = 761317936262414378

    @commands.command("update-welcome")
    @commands.check(utils.is_mod)
    async def cmd_update_welcome(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.message_id)

        embed = discord.Embed(title="Herzlich Willkommen auf dem Discord von Studierenden für Studierende.",
                              description="Disclaimer: Das hier ist kein offizieller Kanal der Fernuni. Hier findet auch keine offizielle Betreuung durch die Fernuni statt. Dieser Discord dient zum Austausch unter Studierenden über einzelne Kurse, um sich gegenseitig helfen zu können, aber auch um über andere Themen in einen Austausch zu treten. Es soll KEIN Ersatz für die Kanäle der Lehrgebiete sein, wie die Newsgroups, Moodle-Foren und was es noch so gibt. Der Discord soll die Möglichkeit bieten, feste Lerngruppen zu finden und sich in diesen gegenseitig zu helfen und zu treffen. Zudem soll er durch den Austausch in den Kanälen auch eine Art flexible Lerngruppe zu einzelnen Kursen ermöglichen. Daher ist unser Apell an euch: Nutzt bitte auch die Betreuungsangebote der entsprechenden Kurse, in die ihr eingeschrieben seid. ")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/avatars/697842294279241749/c7d3063f39d33862e9b950f72ab71165.webp?size=1024")
        embed.add_field(name="Lerngruppen",
                        value="Wenn ihr eine feste Lerngruppe gründen möchtet, dann könnt ihr dafür gerne einen eigenen Textchannel bekommen. Sagt einfach bescheid, dann kann dieser erstellt werden. Ihr könnt dann auch entscheiden, ob nur ihr Zugang zu diesem Channel haben möchtet, oder ob dieser für alle zugänglich sein soll.",
                        inline=False)

        embed.add_field(name="Vorstellung",
                        value="Es gibt einen <#731078162334875693>. Wir würden uns freuen, wenn ihr euch kurz vorstellen würdet. So ist es möglich, Gemeinsamkeiten zu entdecken und man weiß ungefähr, mit wem man es zu tun hat. Hier soll auch gar nicht der komplette Lebenslauf stehen, schreibt einfach das, was ihr so über euch mitteilen möchtet.",
                        inline=False)

        embed.add_field(name="Regeln",
                        value="Es gibt hier auch ein paar, wenige Regeln, an die wir uns alle halten wollen. Diese findet ihr hier https://discordapp.com/channels/353315134678106113/697729059173433344/709475694157234198",
                        inline=False)

        embed.add_field(name="Nachrichten anpinnen",
                        value="Wenn ihr Nachrichten in einem Channel anpinnen möchtet, könnt ihr dafür unseren Bot verwenden. Setzt einfach eine :pushpin: Reaktion auf die entsprechende Nachricht und der pin-bot erledigt den Rest.",
                        inline=False)

        embed.add_field(name="Rollen",
                        value="Außerdem haben wir Rollen für die einzelnen Studiengänge. Das soll es in bestimmten Situationen vereinfachen, zu identifizieren, in welchem Studiengang man eingeschrieben ist. Dadurch lassen sich bestimmte Nachrichten und Fragen besser im Kontext zuordnen und die Fragen können passend zum Studiengang präziser beantwortet werden. Die Rollen, die hierfür derzeit zur Verfügung stehen sind:\nB.Sc. Informatik, B.Sc. Mathematik, B.Sc. Wirtschaftsinformatik, B.Sc. Mathematisch-Technische Softwareentwicklung,\nM.Sc. Informatik, M.Sc. Praktische Informatik, M.Sc. Mathematik, M.Sc. Wirtschaftsinformatik. ",
                        inline=False)

        await message.edit(content="", embed=embed)

        guild = await self.bot.fetch_guild(int(os.getenv('DISCORD_GUILD')))
        roles_cog = self.bot.get_cog("RolesCog")

        print(roles_cog.assignable_roles)

        for emoji in guild.emojis:
            if emoji.name in roles_cog.assignable_roles.keys():
                await message.add_reaction(emoji)

            print(emoji)
