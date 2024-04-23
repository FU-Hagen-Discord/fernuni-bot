import discord
from discord import app_commands, Interaction
from discord.ext import commands

import models
from modals.link_modal import LinkModal, LinkCategoryModal


@app_commands.guild_only()
class Links(commands.GroupCog, name="links", description="Linkverwaltung für Kanäle."):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="show", description="Zeige Links für diesen Kanal an.")
    @app_commands.describe(category="Zeige nur Links für diese Kategorie an.", public="Zeige die Linkliste für alle.")
    async def cmd_show(self, interaction: Interaction, category: str = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public)

        message = "### __Folgende Links sind in diesem Channel hinterlegt__\n"
        if not models.LinkCategory.has_links(interaction.channel_id):
            message = "Für diesen Channel sind noch keine Links hinterlegt."
        elif category and not models.LinkCategory.has_links(interaction.channel_id, category=category):
            message = (f"Für die Kategorie `{category}` sind in diesem Channel keine Links hinterlegt. "
                       f"Versuch es noch mal mit einer anderen Kategorie, oder lass dir mit `/links show` alle Links "
                       f"in diesem Channel ausgeben.")
        else:
            for category in models.LinkCategory.get_categories(interaction.channel_id, category=category):
                message += f"**{category.name}**\n"
                if category.links.count() > 0:
                    for link in category.links:
                        link_text = f"- [{link.title}](<{link.url}>)\n"

                        if len(message) + len(link_text) > 1900:
                            await interaction.followup.send(message, ephemeral=not public)
                            message = ""
                        message += link_text
                else:
                    category.delete_instance()

        await interaction.followup.send(message, ephemeral=not public)

    @app_commands.command(name="add", description="Füge einen neuen Link hinzu.")
    async def cmd_add(self, interaction: Interaction):
        await interaction.response.send_modal(LinkModal())

    @app_commands.command(name="edit-link", description="Einen bestehenden Link in der Liste bearbeiten.")
    @app_commands.describe(category="Kategorie zu der der zu bearbeitende Link gehört.",
                           title="Titel des zu bearbeitenden Links.")
    async def cmd_edit_link(self, interaction: Interaction, category: str, title: str):
        if db_category := models.LinkCategory.get_or_none(models.LinkCategory.channel == interaction.channel_id,
                                                          models.LinkCategory.name == category):
            if link := models.Link.get_or_none(models.Link.title == title, models.Link.category == db_category.id):
                await interaction.response.send_modal(
                    LinkModal(category=link.category.name, link_title=link.title, link=link.url, link_id=link.id,
                              title="Link bearbeiten"))
            else:
                await interaction.response.send_message(content='Ich konnte den Link leider nicht finden.',
                                                        ephemeral=True)
        else:
            await interaction.response.send_message(content='Ich konnte die Kategorie leider nicht finden.',
                                                    ephemeral=True)

    @app_commands.command(name="rename-category", description="Kategorie bearbeiten.")
    @app_commands.describe(category="Zu bearbeitende Kategorie")
    async def cmd_rename_category(self, interaction: Interaction, category: str):
        if not models.LinkCategory.has_links(interaction.channel_id):
            await interaction.response.send_message(content="Für diesen Channel sind noch keine Links hinterlegt.",
                                                    ephemeral=True)
            return

        if db_category := models.LinkCategory.get_or_none(models.LinkCategory.channel == interaction.channel_id,
                                                          models.LinkCategory.name == category):
            await interaction.response.send_modal(LinkCategoryModal(db_category=db_category))
        else:
            await interaction.response.send_message(content='Ich konnte das Thema leider nicht finden.', ephemeral=True)

    @app_commands.command(name="remove-link", description="Einen Link entfernen.")
    @app_commands.describe(topic="Theme zu dem der zu entfernende Link gehört.",
                           title="Titel des zu entfernenden Links.")
    async def cmd_remove_link(self, interaction: Interaction, topic: str, title: str):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()

        if not models.LinkCategory.has_links(interaction.channel_id):
            await interaction.edit_original_response(content="Für diesen Channel sind noch keine Links hinterlegt.")
            return
        if topic_entity := models.LinkCategory.get_or_none(models.LinkCategory.channel == interaction.channel_id,
                                                           models.LinkCategory.name == topic):
            if link := models.Link.get_or_none(models.Link.title == title, models.Link.topic == topic_entity.id):
                link.delete_instance(recursive=True)
                await interaction.edit_original_response(content=f'Link {title} entfernt')
            else:
                await interaction.edit_original_response(content='Ich konnte den Link leider nicht finden.')
        else:
            await interaction.edit_original_response(content='Ich konnte das Thema leider nicht finden.')
            return

    @app_commands.command(name="remove-topic", description="Ein Thema mit allen zugehörigen Links entfernen.")
    @app_commands.describe(topic="Zu entfernendes Thema.")
    async def cmd_remove_topic(self, interaction: Interaction, topic: str):
        await interaction.response.defer(ephemeral=True)
        topic = topic.lower()

        if not models.LinkCategory.has_links(interaction.channel_id):
            await interaction.edit_original_response(content="Für diesen Channel sind noch keine Links hinterlegt.")
            return
        if topic_entity := models.LinkCategory.get_or_none(models.LinkCategory.channel == interaction.channel_id,
                                                           models.LinkCategory.name == topic):
            topic_entity.delete_instance(recursive=True)
            await interaction.edit_original_response(content=f'Thema {topic} mit allen zugehörigen Links entfernt')
        else:
            await interaction.edit_original_response(content='Ich konnte das Thema leider nicht finden.')
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Links(bot))
