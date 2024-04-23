import discord
from discord import Message

from models import CommandText, Command


def get_from_embed(message: Message) -> tuple[str, str, str] | tuple[str, str, None]:
    embed = message.embeds[0]
    fields = {field.name: field.value for field in embed.fields}

    return fields.get("Command"), fields.get("Text"), fields.get("Beschreibung")


class TextCommandView(discord.ui.View):
    def __init__(self, text_commands):
        super().__init__(timeout=None)
        self.text_commands = text_commands

    @discord.ui.button(emoji="👍", style=discord.ButtonStyle.green, custom_id='text_command_view:approve')
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        cmd, text, description = get_from_embed(interaction.message)

        if command := Command.get_or_none(Command.command == cmd):
            CommandText.create(text=text, command=command.id)
        else:
            command = Command.create(command=cmd, description=description)
            CommandText.create(text=text, command=command.id)
            await self.text_commands.register_command(command)
        await interaction.followup.send(content=f"Command `{cmd}` mit Text "
                                                f"`{text}` wurde akzeptiert.")

        await interaction.message.delete()

    @discord.ui.button(emoji="👎", style=discord.ButtonStyle.red, custom_id='text_command_view:decline')
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        cmd, text, _ = get_from_embed(interaction.message)

        await interaction.followup.send(content=f"Command `{cmd}` mit Text "
                                                f"`{text}` wurde abgelehnt.")
        await interaction.message.delete()