import re
import traceback
from typing import Optional

import discord as discord
from discord import ui, TextStyle
from discord.utils import MISSING

import models
import utils


class InvalidLinkError(Exception):
    pass


class LinkDoesNotExistError(Exception):
    pass


class TextCommandModal(ui.Modal, title='Neues Text Command hinzufügen'):
    def __init__(self, *, text_commands=None, cmd: str = "", text: str = "", description: str = "",
                 title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        self.text_commands = text_commands
        self.cmd = cmd
        self.text.default = text
        self.description.default = description

    text = ui.TextInput(label='Text', style=TextStyle.long)
    description = ui.TextInput(label='Beschreibung', max_length=100, placeholder="Beschreibung des Commands.")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Verarbeite Command...", ephemeral=True)

        if await self.text_commands.add_command(self.cmd, self.text.value, self.description.value, interaction.guild_id):
            await interaction.edit_original_response(content="Dein Command wurde erfolgreich hinzugefügt!")
        else:
            await interaction.edit_original_response(
                content="Das Command, dass du hinzufügen möchtest existiert bereits.")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if type(error) in [InvalidLinkError, LinkDoesNotExistError]:
            await interaction.response.send_message(content=error, ephemeral=True)
        else:
            await interaction.response.send_message(content="Fehler beim Hinzufügen eines Commands/Texts.",
                                                    ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)
