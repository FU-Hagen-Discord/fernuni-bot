import json

import disnake
from disnake.ext import commands
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
        brief="Zeigt die Links an, die in diesem Channel (evtl. unter Berücksichtigung eines Themas) hinterlegt sind.",
        parameters={
            "topic": "*(optional)* Schränkt die angezeigten Links auf das übergebene Thema ein. "
        }
    )
    @commands.group(name="links", pass_context=True, invoke_without_command=True)
    async def cmd_links(self, ctx, topic=None):
        if channel_links := self.links.get(str(ctx.channel.id)):
            embed = disnake.Embed(title=f"Folgende Links sind in diesem Channel hinterlegt:\n")
            if topic:
                topic = topic.lower()
                if topic_links := channel_links.get(topic):
                    value = f""
                    for title, link in topic_links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=topic.capitalize(), value=value, inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        f" Für das Thema `{topic}` sind in diesem Channel keine Links hinterlegt. Versuch es noch mal "
                        f"mit einem anderen Thema, oder lass dir mit `!links` alle Links in diesem Channel ausgeben")
            else:
                for topic, links in channel_links.items():
                    value = f""
                    for title, link in links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=topic.capitalize(), value=value, inline=False)
                await ctx.send(embed=embed)
        else:
            await ctx.send("Für diesen Channel sind noch keine Links hinterlegt.")

    @help(
        category="links",
        syntax="!links add <topic> <link> <title...>",
        brief="Fügt einen Link zum Channel hinzu.",
        parameters={
            "topic": "Name des Themas, dem der Link zugeordnet werden soll. ",
            "link": "die URL, die aufgerufen werden soll (z. B. https://www.fernuni-hagen.de). ",
            "title...": "Titel, der für diesen Link angezeigt werden soll (darf Leerzeichen enthalten). "
        },
        description="Die mit !links add zu einem Kanal hinzugefügten Links können über das Kommando !links in diesem "
                    "Kanal wieder abgerufen werden.",
        command_group="links"
    )
    @cmd_links.command(name="add")
    async def cmd_add_link(self, ctx, topic, link, *title):
        topic = topic.lower()
        if not (channel_links := self.links.get(str(ctx.channel.id))):
            self.links[str(ctx.channel.id)] = {}
            channel_links = self.links.get(str(ctx.channel.id))

        if not (topic_links := channel_links.get(topic)):
            channel_links[topic] = {}
            topic_links = channel_links.get(topic)

        self.add_link(topic_links, link, " ".join(title))
        self.save_links()

    def add_link(self, topic_links, link, title):
        if topic_links.get(title):
            self.add_link(topic_links, link, title + str(1))
        else:
            topic_links[title] = link

    @help(
        category="links",
        syntax="!links remove-link <topic> <title...>",
        brief="Löscht einen Link aus dem Channel.",
        parameters={
            "topic": "Name des Themas, aus dem der Link entfernt werden soll. ",
            "title...": "Titel des Links, der entfernt werden soll. "
        },
        description="Mit !links remove-link kann ein fehlerhafter oder veralteter Link aus der Linkliste des Channels "
                    "entfernt werden.",
        command_group="links"
    )
    @cmd_links.command(name="remove-link", aliases=['rl'])
    async def cmd_remove_link(self, ctx, topic, *title):
        topic = topic.lower()
        title = " ".join(title)

        if channel_links := self.links.get(str(ctx.channel.id)):
            if topic_links := channel_links.get(topic):
                if title in topic_links:
                    topic_links.pop(title)
                    if not topic_links:
                        channel_links.pop(topic)
                else:
                    await ctx.channel.send('Ich konnte den Link leider nicht finden.')
            else:
                await ctx.channel.send('Ich konnte das Thema leider nicht finden.')
        else:
            await ctx.channel.send('Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()

    @help(
        category="links",
        syntax="!links remove-topic <topic>",
        brief="Löscht eine komplette Themenkategorie aus dem Channel.",
        parameters={
            "topic": "Name des Themas, das entfernt werden soll. ",
        },
        description="Mit !links remove-topic kann ein Thema aus der Linkliste des Channels entfernt werden.",
        command_group="links"
    )
    @cmd_links.command(name="remove-topic", aliases=['rt'])
    async def cmd_remove_topic(self, ctx, topic):
        topic = topic.lower()

        if channel_links := self.links.get(str(ctx.channel.id)):
            if channel_links.get(topic):
                channel_links.pop(topic)
            else:
                await ctx.channel.send('Ich konnte das Thema leider nicht finden.')
        else:
            await ctx.channel.send('Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()


    @help(
        category="links",
        syntax="!links edit-link <topic> <title> <new_title> <new_topic?> <new_link?>",
        brief="Bearbeitet einen Link.",
        parameters={
            "topic": "Name des Themas, aus dem der zu bearbeitende Link stammt. ",
            "title": "Titel des Links, der bearbeitet werden soll. ",
            "new_title": "Neuer Titel für den geänderten Link. ",
            "new_topic": "*(optional)* Neues Thema für den geänderten Link. ",
            "new_link": "*(optional)* Der neue Link. "
        },
        description="Mit !links edit-link kann ein fehlerhafter oder veralteter Link bearbeitet werden.",
        command_group="links"
    )
    @cmd_links.command(name="edit-link", aliases=["el"])
    async def cmd_edit_link(self, ctx, topic, title, new_title, new_topic=None, new_link=None):
        topic = topic.lower()

        if not new_topic:
            new_topic = topic

        if not new_link:
            if channel_links := self.links.get(str(ctx.channel.id)):
                if topic_links := channel_links.get(topic):
                    if topic_links.get(title):
                        new_link = topic_links.get(title)
                    else:
                        await ctx.channel.send('Ich konnte den Link leider nicht finden.')
                else:
                    await ctx.channel.send('Ich konnte das Thema leider nicht finden.')
            else:
                await ctx.channel.send('Für diesen Channel sind keine Links hinterlegt.')

        await self.cmd_remove_link(ctx, topic, title)
        await self.cmd_add_link(ctx, new_topic, new_link, new_title)

    @help(
        category="links",
        syntax="!links edit-topic <topic> <new_topic>",
        brief="Bearbeitet den Namen eines Themas.",
        parameters={
            "topic": "Name des Themas, das bearbeitet werden soll. ",
            "new_topic": "Neuer Name des Themas. "
        },
        description="Mit !links edit-topic kann der Name eines Themas geändert werden.",
        command_group="links"
    )
    @cmd_links.command(name="edit-topic", aliases=["et"])
    async def cmd_edit_topic(self, ctx, topic, new_topic):
        topic = topic.lower()
        new_topic = new_topic.lower()
        if channel_links := self.links.get(str(ctx.channel.id)):
            if topic_links := channel_links.get(topic):
                channel_links[new_topic] = topic_links
                await self.cmd_remove_topic(ctx, topic)
            else:
                await ctx.channel.send('Ich konnte das Thema leider nicht finden.')
        else:
            await ctx.channel.send('Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
