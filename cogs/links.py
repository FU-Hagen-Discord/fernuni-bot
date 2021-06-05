import json

import discord
from discord.ext import commands
from cogs.help import help, handle_error, help_category


@help_category("links", "Links", "Feature zum Verwalten von Links innerhalb eines Channels.")
class Links(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.links = {}
        self.links_file = "data/links.json"
        self.load_links()

    def load_links(self):
        links_file = open(self.links_file, 'r')
        self.links = json.load(links_file)

    def save_links(self):
        links_file = open(self.links_file, 'w')
        json.dump(self.links, links_file)

    @help(
        category="links",
        brief="Zeigt die Links an, die in diesem Channel (evtl. unter Berücksichtigung einer Kategorie) hinterlegt sind.",
        parameters={
            "category": "*(optional)* Schränkt die angezeigten Links auf die übergebene Kategorie ein. "
        }
    )
    @commands.command(name="links")
    async def cmd_links(self, ctx, category=None):
        if channel_links := self.links.get(str(ctx.channel.id)):
            embed = discord.Embed(title=f"Folgende Links sind in diesem Channel hinterlegt:\n")
            if category:
                category = category.lower()
                if group_links := channel_links.get(category):
                    value = f""
                    for title, link in group_links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=category.capitalize(), value=value, inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        f" Für die Kategorie `{category}` sind in diesem Channel keine Links hinterlegt. Versuch es noch mal mit einer anderen Gruppe, oder lass dir mit `!links` alle Links in diesem Channel ausgeben")
            else:
                for category, links in channel_links.items():
                    value = f""
                    for title, link in links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=category.capitalize(), value=value, inline=False)
                await ctx.send(embed=embed)
        else:
            await ctx.send("Für diesen Channel sind noch keine Links hinterlegt.")

    @help(
        category="links",
        syntax="!add-link <category> <link> <title...>",
        brief="Fügt einen Link zum Channel hinzu.",
        parameters={
            "category": "Name der Kategorie, der der Link zugeordnet werden soll. ",
            "link": "die URL, die aufgerufen werden soll (z. B. https://www.fernuni-hagen.de). ",
            "title...": "Titel, der für diesen Link angezeigt werden soll (darf Leerzeichen enthalten). ",
        },
        description="Die mit !add-link zu einem Kanal hinzugefügten Links können über das Kommando !links in diesem Kanal wieder abgerufen werden."
    )
    @commands.command(name="add-link")
    async def cmd_add_link(self, ctx, category, link, *title):
        category = category.lower()
        if not (channel_links := self.links.get(str(ctx.channel.id))):
            self.links[str(ctx.channel.id)] = {}
            channel_links = self.links.get(str(ctx.channel.id))

        if not (group_links := channel_links.get(category)):
            channel_links[category] = {}
            group_links = channel_links.get(category)

        self.add_link(group_links, link, " ".join(title))
        self.save_links()

    def add_link(self, group_links, link, title):
        if group_links.get(title):
            self.add_link(group_links, link, title + str(1))
        else:
            group_links[title] = link

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
