import json

import discord
from discord import app_commands, Interaction
from discord.ext import commands


@app_commands.guild_only()
class Links(commands.GroupCog, name="links", description="Linkverwaltung für Kanäle."):
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

    @app_commands.command(name="list", description="Liste Links für diesen Kanal auf.")
    @app_commands.describe(topic="Zeige nur Links für dieses Thema an.", public="Zeige die Linkliste für alle.")
    async def cmd_list(self, interaction: Interaction, topic: str = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public)

        if channel_links := self.links.get(str(interaction.channel_id)):
            embed = discord.Embed(title=f"Folgende Links sind in diesem Channel hinterlegt:\n")
            if topic:
                topic = topic.lower()
                if topic_links := channel_links.get(topic):
                    value = f""
                    for title, link in topic_links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=topic.capitalize(), value=value, inline=False)
                    await interaction.edit_original_response(embed=embed)
                else:
                    await interaction.edit_original_response(
                        content=f"Für das Thema `{topic}` sind in diesem Channel keine Links hinterlegt. Versuch es "
                                f"noch mal mit einem anderen Thema, oder lass dir mit `!links` alle Links in diesem "
                                f"Channel ausgeben")
            else:
                for topic, links in channel_links.items():
                    value = f""
                    for title, link in links.items():
                        value += f"- [{title}]({link})\n"
                    embed.add_field(name=topic.capitalize(), value=value, inline=False)
                await interaction.edit_original_response(embed=embed)
        else:
            await interaction.edit_original_response(content="Für diesen Channel sind noch keine Links hinterlegt.")

    @app_commands.command(name="add", description="Füge einen neuen Link hinzu.")
    @app_commands.describe(topic="Thema, zu dem dieser Link hinzugefügt werden soll.",
                           link="Link, der hinzugefügt werden soll.", title="Titel des Links.")
    async def cmd_add(self, interaction: Interaction, topic: str, link: str, title: str):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()
        if not (channel_links := self.links.get(str(interaction.channel_id))):
            self.links[str(interaction.channel_id)] = {}
            channel_links = self.links.get(str(interaction.channel_id))

        if not (topic_links := channel_links.get(topic)):
            channel_links[topic] = {}
            topic_links = channel_links.get(topic)

        self.add_link(topic_links, link, title)
        self.save_links()
        await interaction.edit_original_response(content="Link hinzugefügt.")

    def add_link(self, topic_links, link, title):
        if topic_links.get(title):
            self.add_link(topic_links, link, title + str(1))
        else:
            topic_links[title] = link

    @app_commands.command(name="remove-link", description="Einen Link entfernen.")
    @app_commands.describe(topic="Theme zu dem der zu entfernende Link gehört.",
                           title="Titel des zu entfernenden Links.")
    async def cmd_remove_link(self, interaction: Interaction, topic: str, title: str):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()

        if channel_links := self.links.get(str(interaction.channel_id)):
            if topic_links := channel_links.get(topic):
                if title in topic_links:
                    topic_links.pop(title)
                    if not topic_links:
                        channel_links.pop(topic)
                    await interaction.edit_original_response(content="Link entfernt.")
                else:
                    await interaction.edit_original_response(content='Ich konnte den Link leider nicht finden.')
            else:
                await interaction.edit_original_response(content='Ich konnte das Thema leider nicht finden.')
        else:
            await interaction.edit_original_response(content='Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()

    @app_commands.command(name="remove-topic", description="Ein Thema mit allen zugehörigen Links entfernen.")
    @app_commands.describe(topic="Zu entfernendes Thema.")
    async def cmd_remove_topic(self, interaction: Interaction, topic: str):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()

        if channel_links := self.links.get(str(interaction.channel_id)):
            if channel_links.get(topic):
                channel_links.pop(topic)
                await interaction.edit_original_response(content="Thema entfernt")
            else:
                await interaction.edit_original_response(content='Ich konnte das Thema leider nicht finden.')
        else:
            await interaction.edit_original_response(content='Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()

    @app_commands.command(name="edit-link", description="Einen bestehenden Link in der Liste bearbeiten.")
    @app_commands.describe(topic="Thema zu dem der zu bearbeitende Link gehört.",
                           title="Titel des zu bearbeitenden Links.", new_title="Neuer Titel des Links.",
                           new_topic="Neues Thema des Links.", new_link="Neuer Link.")
    async def cmd_edit_link(self, interaction: Interaction, topic: str, title: str, new_title: str,
                            new_topic: str = None, new_link: str = None):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()
        new_topic = new_topic.lower() if new_topic else topic

        if channel_links := self.links.get(str(interaction.channel_id)):
            if topic_links := channel_links.get(topic):
                if topic_links.get(title):
                    new_link = new_link if new_link else topic_links.get(title)
                    del topic_links[title]
                else:
                    await interaction.edit_original_response(content='Ich konnte den Link leider nicht finden.')
                    return
            else:
                await interaction.edit_original_response(content='Ich konnte das Thema leider nicht finden.')
                return
            new_title = new_title if new_title else title
            if topic_links := channel_links.get(new_topic):
                topic_links[new_title] = new_link
            else:
                channel_links[new_topic] = {new_title: new_link}
            await interaction.edit_original_response(content="Link erfolgreich editiert.")
        else:
            await interaction.edit_original_response(content='Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()

    @app_commands.command(name="edit-topic", description="Thema bearbeiten.")
    @app_commands.describe(topic="Zu bearbeitendes Thema", new_topic="Neues Thema")
    async def cmd_edit_topic(self, interaction: Interaction, topic: str, new_topic: str):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()
        new_topic = new_topic.lower()

        if channel_links := self.links.get(str(interaction.channel_id)):
            if topic_links := channel_links.get(topic):
                channel_links[new_topic] = topic_links
                del channel_links[topic]
                await interaction.edit_original_response(content="Thema aktualisiert.")
            else:
                await interaction.edit_original_response(content='Ich konnte das Thema leider nicht finden.')
        else:
            await interaction.edit_original_response(content='Für diesen Channel sind keine Links hinterlegt.')

        self.save_links()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Links(bot))
