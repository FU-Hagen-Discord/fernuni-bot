import json

import discord
from discord.ext import commands
from tinydb import where

from cogs.help import help, handle_error, help_category


@help_category("links", "Links", "Feature zum Verwalten von Links innerhalb eines Channels.")
class Links(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def group_table(self):
        return self.bot.db.table('link_group')

    @property
    def link_table(self):
        return self.bot.db.table('link')

    @help(
        category="links",
        brief="Zeigt die Links an, die in diesem Channel hinterlegt sind.",
    )
    @commands.command(name="links")
    async def cmd_links(self, ctx):
        if groups := self.group_table.search(where("channel_id") == ctx.channel.id):
            embed = discord.Embed(title=f"Folgende Links sind in diesem Channel hinterlegt:\n")
            for group in groups:
                value = f""
                for link in self.link_table.search(where("group_id") == group.doc_id):
                    value += f"- [{link['title']}]({link['url']})\n"
                embed.add_field(name=group["group_title"], value=value, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Für diesen Channel sind noch keine Links hinterlegt.")

    @help(
        category="links",
        syntax="!add-link <group> <link> <title...>",
        brief="Fügt einen Link zum Channel hinzu.",
        parameters={
            "group": "Name der Gruppe, die der Link zugeordnet werden soll. ",
            "link": "die URL, die aufgerufen werden soll (z. B. https://www.fernuni-hagen.de). ",
            "title...": "Titel, der für diesen Link angezeigt werden soll (darf Leerzeichen enthalten). ",
        },
        description="Die mit !add-link zu einem Kanal hinzugefügten Links können über das Kommando !links in diesem Kanal wieder abgerufen werden."
    )
    @commands.command(name="add-link")
    async def cmd_add_link(self, ctx, group_title, url, *, title):
        if group := self.group_table.get(where("channel_id") == ctx.channel.id and where("group_title") == group_title):
            pass
        else:
            group_id = self.group_table.insert({"channel_id": ctx.channel.id, "group_title": group_title})
            group = self.group_table.get(doc_id=group_id)

        self.link_table.insert({"group_id": group.doc_id, "url": url, "title": title})

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
