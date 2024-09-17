import re
import traceback
from typing import Optional

import discord as discord
from discord import ui
from discord.utils import MISSING

import models


class InvalidLinkError(Exception):
    pass


class LinkDoesNotExistError(Exception):
    pass


class LinkModal(ui.Modal, title='Link hinzufügen'):
    def __init__(self, *, category: str = None, link_title: str = None, link: str = None, link_id: int = None,
                 title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        self.category.default = category
        self.link_title.default = link_title
        self.link.default = link
        self.link_id = link_id

    category = ui.TextInput(label='Kategorie')
    link_title = ui.TextInput(label='Titel')
    link = ui.TextInput(label='Link')

    def validate_link(self):
        if not re.match("^https?://.+", self.link.value):
            raise InvalidLinkError(f"`{self.link}` ist kein gültiger Link")

    async def on_submit(self, interaction: discord.Interaction):
        self.validate_link()
        db_category = models.LinkCategory.get_or_create(channel=interaction.channel_id, name=self.category)

        if self.link_id is None:
            models.Link.create(url=self.link, title=self.link_title, category=db_category[0].id)
            await interaction.response.send_message(content="Link erfolgreich hinzugefügt.", ephemeral=True)
        else:
            if link := models.Link.get_or_none(models.Link.id == self.link_id):
                link_category = link.category
                link.update(title=self.link_title, url=self.link, category=db_category[0].id).where(
                    models.Link.id == link.id).execute()

                if link_category.id != db_category[0].id and link.category.links.count() == 0:
                    link_category.delete_instance()
            else:
                raise LinkDoesNotExistError(f"Der Link `{self.link_title}` existiert nicht.")

            await interaction.response.send_message(content="Link erfolgreich bearbeitet.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if type(error) in [InvalidLinkError, LinkDoesNotExistError]:
            await interaction.response.send_message(content=error, ephemeral=True)
        else:
            await interaction.response.send_message(content="Fehler beim Hinzufügen/Bearbeiten eines Links.",
                                                    ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


class LinkCategoryModal(ui.Modal, title='Kategorie umbenennen'):
    def __init__(self, *, db_category: str = None, link_id: int = None,
                 title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        self.db_category = db_category
        self.category.default = db_category.name
        self.link_id = link_id

    category = ui.TextInput(label='Kategorie')

    async def on_submit(self, interaction: discord.Interaction):
        self.db_category.update(name=self.category).where(models.LinkCategory.id == self.db_category.id).execute()
        await interaction.response.send_message(content="Kategorie erfolgreich umbenannt.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(content=f"Fehler beim umbenennen der Kategorie `{self.category}`.",
                                                ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)
