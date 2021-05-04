import json

import discord
from discord.ext import commands
from help.help import help, handle_error


class LinksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.links = {}
        self.links_file = "links.json"
        self.load_links()

    def load_links(self):
        links_file = open(self.links_file, 'r')
        self.links = json.load(links_file)

    def save_links(self):
        links_file = open(self.links_file, 'w')
        json.dump(self.links, links_file)

    @help(
      brief="Zeigt die Links an, die in diesem Channel (evtl. unter Berücksichtigung einer Gruppe) hinterlegt sind.",
      parameters={
        "group": "*(optional)* Schränkt die angezeigten Links auf die übergebene Gruppe ein. "
      }
    )
    @commands.command(name="links")
    async def cmd_links(self, ctx, group=None):
        if channel_links := self.links.get(str(ctx.channel.id)):
            embed = discord.Embed(title=f"Folgende Links sind in diesem Channel hinterlegt:\n")
            if group:
                group = group.lower()
                if group_links := channel_links.get(group):
                    value = f""
                    for title, link in group_links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=group.capitalize(), value=value, inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        f" Für die Gruppe `{group}` sind in diesem Channel keine Links hinterlegt. Versuch es noch mal mit einer anderen Gruppe, oder lass dir mit `!links` alle Links in diesem Channel ausgeben")
            else:
                for group, links in channel_links.items():
                    value = f""
                    for title, link in links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=group.capitalize(), value=value, inline=False)
                await ctx.send(embed=embed)
        else:
            await ctx.send("Für diesen Channel sind noch keine Links hinterlegt.")

    @help(
      syntax="!add-link <group> <link> <title...>",
      brief="Fügt einen Link zum Channel hinzu.",
      parameters={
        "group":"Name der Gruppe, die der Link zugeordnet werden soll. ",
        "link":"die URL, die aufgerufen werden soll (z. B. https://www.fernuni-hagen.de). ",
        "title...":"Titel, der für diesen Link angezeigt werden soll (darf Leerzeichen enthalten). ",
      },
      description="Die mit !add-link zu einem Kanal hinzugefügten Links können über das Kommando !links in diesem Kanal wieder abgerufen werden."
    )
    @commands.command(name="add-link")
    async def cmd_add_link(self, ctx, group, link, *title):
        if not (channel_links := self.links.get(str(ctx.channel.id))):
            self.links[str(ctx.channel.id)] = {}
            channel_links = self.links.get(str(ctx.channel.id))

        if not (group_links := channel_links.get(group)):
            channel_links[group] = {}
            group_links = channel_links.get(group)

        self.add_link(group_links, link, " ".join(title))
        self.save_links()

    def add_link(self, group_links, link, title):
        if group_links.get(title):
            self.add_link(group_links, link, title + str(1))
        else:
            group_links[title] = link
        
    async def cog_command_error(self, ctx, error):
      await handle_error(ctx, error)
