from discord import app_commands, Interaction
from discord.ext import commands

import models
from modals.link_modal import LinkModal, LinkCategoryModal


@app_commands.guild_only()
class Links(commands.GroupCog, name="links", description="Linkverwaltung für Kanäle."):
    def __init__(self, bot):
        self.bot = bot

    # Helper Methods
    async def _ensure_has_links(self, interaction: Interaction) -> bool:
        """Prüft ob der Kanal Links hat. Sendet Fehlermeldung und gibt False zurück wenn nicht."""
        if not models.LinkCategory.has_links(interaction.channel_id):
            await interaction.edit_original_response(
                content="Für diesen Channel sind noch keine Links hinterlegt."
            )
            return False
        return True

    async def _get_category_or_error(
            self, interaction: Interaction, category_name: str, respond_method="edit"
    ) -> models.LinkCategory | None:
        """Sucht eine Kategorie oder sendet Fehlermeldung."""
        category = models.LinkCategory.get_or_none(
            models.LinkCategory.channel == interaction.channel_id,
            models.LinkCategory.name == category_name
        )
        if not category:
            method = getattr(interaction, f"{respond_method}_original_response")
            await method(content="Ich konnte die Kategorie leider nicht finden.")
        return category

    async def _get_link_or_error(
            self, interaction: Interaction, title: str, category: models.LinkCategory, respond_method="send_message"
    ) -> models.Link | None:
        """Sucht einen Link oder sendet Fehlermeldung."""
        link = models.Link.get_or_none(
            models.Link.title == title,
            models.Link.category == category.id
        )
        if not link:
            if respond_method == "send_message":
                await interaction.response.send_message(
                    content="Ich konnte den Link leider nicht finden.",
                    ephemeral=True
                )
            else:
                await interaction.edit_original_response(
                    content="Ich konnte den Link leider nicht finden."
                )
        return link

    @app_commands.command(name="show", description="Zeige Links für diesen Kanal an.")
    @app_commands.describe(category="Zeige nur Links für diese Kategorie an.", public="Zeige die Linkliste für alle.")
    async def cmd_show(self, interaction: Interaction, category: str = None, public: bool = True):
        await interaction.response.defer(ephemeral=not public)

        if not models.LinkCategory.has_links(interaction.channel_id):
            await interaction.followup.send(
                "Für diesen Channel sind noch keine Links hinterlegt.",
                ephemeral=not public
            )
            return

        if category and not models.LinkCategory.has_links(interaction.channel_id, category=category):
            await interaction.followup.send(
                (f"Für die Kategorie `{category}` sind in diesem Channel keine Links hinterlegt. "
                 f"Versuch es noch mal mit einer anderen Kategorie, oder lass dir mit `/links show` alle Links "
                 f"in diesem Channel ausgeben."),
                ephemeral=not public
            )
            return

        message = "### __Folgende Links sind in diesem Channel hinterlegt__\n"
        for cat in models.LinkCategory.get_categories(interaction.channel_id, category=category):
            message += f"**{cat.name}**\n"
            if cat.links.count() > 0:
                for link in cat.links:
                    link_text = f"- [{link.title}](<{link.url}>)\n"
                    if len(message) + len(link_text) > 1900:
                        await interaction.followup.send(message, ephemeral=not public)
                        message = ""
                    message += link_text

        if message.strip():
            await interaction.followup.send(message, ephemeral=not public)

    @app_commands.command(name="add", description="Füge einen neuen Link hinzu.")
    async def cmd_add(self, interaction: Interaction):
        await interaction.response.send_modal(LinkModal())

    @app_commands.command(name="edit-link", description="Einen bestehenden Link in der Liste bearbeiten.")
    @app_commands.describe(category="Kategorie zu der der zu bearbeitende Link gehört.",
                           title="Titel des zu bearbeitenden Links.")
    async def cmd_edit_link(self, interaction: Interaction, category: str, title: str):
        if db_category := await self._get_category_or_error(interaction, category, respond_method="send"):
            if link := await self._get_link_or_error(interaction, title, db_category, respond_method="send_message"):
                await interaction.response.send_modal(
                    LinkModal(category=link.category.name, link_title=link.title, link=link.url, link_id=link.id,
                              title="Link bearbeiten"))

    @app_commands.command(name="rename-category", description="Kategorie bearbeiten.")
    @app_commands.describe(category="Zu bearbeitende Kategorie")
    async def cmd_rename_category(self, interaction: Interaction, category: str):
        await interaction.response.defer(ephemeral=True)

        if not await self._ensure_has_links(interaction):
            return

        if db_category := await self._get_category_or_error(interaction, category, respond_method="edit"):
            await interaction.followup.send_modal(LinkCategoryModal(db_category=db_category))

    @app_commands.command(name="remove-link", description="Einen Link entfernen.")
    @app_commands.describe(category="Kategorie zu der der zu entfernende Link gehört.",
                           title="Titel des zu entfernenden Links.")
    async def cmd_remove_link(self, interaction: Interaction, category: str, title: str):
        await interaction.response.defer(ephemeral=True)

        if not await self._ensure_has_links(interaction):
            return

        if db_category := await self._get_category_or_error(interaction, category, respond_method="edit"):
            if link := await self._get_link_or_error(interaction, title, db_category, respond_method="edit"):
                link.delete_instance(recursive=True)
                await interaction.edit_original_response(content=f"Link '{title}' entfernt")

    @app_commands.command(name="remove-category", description="Eine Kategorie mit allen zugehörigen Links entfernen.")
    @app_commands.describe(category="Zu entfernende Kategorie.")
    async def cmd_remove_category(self, interaction: Interaction, category: str):
        await interaction.response.defer(ephemeral=True)

        if not await self._ensure_has_links(interaction):
            return

        if db_category := await self._get_category_or_error(interaction, category, respond_method="edit"):
            db_category.delete_instance(recursive=True)
            await interaction.edit_original_response(
                content=f"Kategorie '{category}' mit allen zugehörigen Links entfernt"
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Links(bot))
