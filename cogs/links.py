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
    @commands.group(name="links", pass_context=True, invoke_without_command=True)
    async def cmd_links(self, ctx, category=None):
        if channel_links := self.links.get(str(ctx.channel.id)):
            embed = discord.Embed(title=f"Folgende Links sind in diesem Channel hinterlegt:\n")
            """
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
            """
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
        syntax="!links add <category> <link> <title...>",
        brief="Fügt einen Link zum Channel hinzu.",
        parameters={
            "category": "Name der Kategorie, der der Link zugeordnet werden soll. ",
            "link": "die URL, die aufgerufen werden soll (z. B. https://www.fernuni-hagen.de). ",
            "title...": "Titel, der für diesen Link angezeigt werden soll (darf Leerzeichen enthalten). ",
        },
        description="Die mit !links add zu einem Kanal hinzugefügten Links können über das Kommando !links in diesem Kanal wieder abgerufen werden."
    )
    @cmd_links.command(name="add")
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

    @help(
        category="links",
        syntax="!links remove <category> <title...?>",
        brief="Löscht eine Kategorie oder einen Link aus dem Channel.",
        parameters={
            "category": "Name der Kategorie, aus der der Link entfernt werden soll. ",
            "title...": "Titel des Links, der entfernt werden soll. ",
        },
        description="Mit !links remove kann eine ganze Kategorie oder ein einzelner fehlerhafter oder veralteter Link "
                    "aus der Linkliste des Channels entfernt werden. Wenn die Kategorie länger als ein Wort ist, muss "
                    "sie in Anführungszeichen gesetzt werden."
    )
    @cmd_links.command(name="remove")
    async def cmd_remove_link(self, ctx, category, *title):
        category = category.lower()

        if channel_links := self.links.get(str(ctx.channel.id)):
            if group_links := channel_links.get(category):
                if title:
                    title = " ".join(title)
                    if group_links.get(title):
                        group_links.pop(title)
                    else:
                        await ctx.channel.send('Ich konnte den Link leider nicht finden.')
                else:
                    channel_links.pop(category)
            else:
                await ctx.channel.send('Ich konnte die Kategorie leider nicht finden.')
        else:
            await ctx.channel.send('Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()


    """
    //TODO:
    !links edit-category - Titel editieren
    """

    @help(
        category="links",
        syntax="!links edit <category> <title> <new_category> <new_link> <new_title...>",
        brief="Bearbeitet einen Link.",
        parameters={
            "category": "Name der Kategorie, aus der der zu bearbeitende Link stammt. ",
            "title": "Titel des Links, der bearbeitet werden soll. ",
            "new_category": "Neue Kategorie für den geänderten Link. ",
            "new_link": "Der neue Link. ",
            "new_title...": "Neuer Titel für den geänderten Link. "
        },
        description="Mit !links edit kann ein fehlerhafter oder veralteter Link bearbeitet werden."
    )
    @cmd_links.command(name="edit")
    async def cmd_edit_link(self, ctx, category, title, new_category, new_link, *new_title):
        await self.cmd_remove_link(ctx, category, title)
        await self.cmd_add_link(ctx, new_category, new_link, *new_title)



    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
