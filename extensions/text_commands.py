import random
import re

import discord
from discord import app_commands, Interaction
from discord.ext import commands

import utils
from modals.text_command_modal import TextCommandModal
from models import Command, CommandText
from views.text_command_view import TextCommandView


@app_commands.guild_only()
class TextCommands(commands.GroupCog, name="commands", description="Text Commands auflisten und verwalten"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list", description="Listet die Text Commands dieses Servers auf.")
    async def cmd_list(self, interaction: Interaction, cmd: str = None):
        await interaction.response.defer(ephemeral=True)
        items = []
        if cmd:
            if command := Command.get_or_none(Command.command == cmd):
                items = [command_text.text for command_text in command.texts]

            if len(items) == 0:
                await interaction.edit_original_response(content=f"{cmd} ist kein verfügbares Text-Command")
                return
        else:
            for command in Command.select():
                if command.texts.count() > 0:
                    items.append(command.command)

        answer = f"Text Commands:\n" if cmd is None else f"Für {cmd} hinterlegte Texte:\n"
        first = True
        for i, item in enumerate(items):
            if len(answer) + len(item) > 2000:
                if first:
                    await interaction.edit_original_response(content=answer)
                    first = False
                else:
                    await interaction.followup.send(answer, ephemeral=True)
                answer = f""

            answer += f"{i}: {item}\n"

        if first:
            await interaction.edit_original_response(content=answer)
        else:
            await interaction.followup.send(answer, ephemeral=True)

    @app_commands.command(name="add",
                          description="Ein neues Text Command hinzufügen, oder zu einem bestehenden einen weiteren Text hinzufügen")
    @app_commands.describe(cmd="Command. Bsp: \"link\" für das Command \"/link\".",
                           text="Text, der bei Benutzung des Commands ausgegeben werden soll.")
    async def cmd_add(self, interaction: Interaction, cmd: str, text: str):
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", cmd):
            await interaction.response.send_message(
                "Ein Command darf nur aus Kleinbuchstaben und Zahlen bestehen, die durch Bindestriche getrennt werden können.",
                ephemeral=True)
            return

        command = Command.get_or_none(Command.command == cmd)
        description = command.description if command else ""
        await interaction.response.send_modal(
            TextCommandModal(text_commands=self, cmd=cmd, text=text, description=description))

    @app_commands.command(name="edit", description="Bearbeite bestehende Text Commands")
    @app_commands.describe(cmd="Command, dass du bearbeiten möchtest", id="ID des zu bearbeitenden Texts",
                           text="Neuer Text, der statt des alten ausgegeben werden soll.")
    async def cmd_edit(self, interaction: Interaction, cmd: str, id: int, text: str):
        await interaction.response.defer(ephemeral=True)

        if not utils.is_mod(interaction.user, self.bot):
            await interaction.edit_original_response(content="Du hast nicht die notwendigen Berechtigungen, "
                                                             "um dieses Command zu benutzen!")
            return

        if command := Command.get_or_none(Command.command == cmd):
            command_texts = list(command.texts)
            if 0 <= id < len(command_texts):
                CommandText.update(text=text).where(CommandText.id == command_texts[id].id).execute()
                await interaction.edit_original_response(
                    content=f"Text {id} für Command {cmd} wurde erfolgreich geändert")
            else:
                await interaction.edit_original_response(content="Ungültiger Index")
        else:
            await interaction.edit_original_response(content=f"Command `{cmd}` nicht vorhanden!")

    @app_commands.command(name="remove",
                          description="Entferne ein gesamtes Command oder einen einzelnen Text von einem Command.")
    @app_commands.describe(cmd="Command, dass du entfernen möchtest, oder von dem du einen Text entfernen möchtest.",
                           id="ID des zu entfernenden Texts.")
    async def cmd_command_remove(self, interaction: Interaction, cmd: str, id: int = None):
        await interaction.response.defer(ephemeral=True)

        if not utils.is_mod(interaction.user, self.bot):
            await interaction.edit_original_response(content="Du hast nicht die notwendigen Berechtigungen, "
                                                             "um dieses Command zu benutzen!")
            return

        if command := Command.get_or_none(Command.command == cmd):
            if id is None:
                await self.remove_command(command)
                await interaction.edit_original_response(content=f"Text Command `{cmd}` wurde erfolgreich entfernt.")
            else:
                command_texts = list(command.texts)
                if 0 <= id < len(command_texts):
                    await self.remove_text(command, command_texts, id)
                    await interaction.edit_original_response(
                        content=f"Text {id} für Command `{cmd}` wurde erfolgreich entfernt")
                else:
                    await interaction.edit_original_response(content=f"Ungültiger Index")
        else:
            await interaction.edit_original_response(content=f"Command `{cmd}` nicht vorhanden!")

    async def add_command(self, cmd: str, text: str, description: str, guild_id: int):
        mod_channel_id = self.bot.get_settings(guild_id).modmail_channel_id
        mod_channel = await self.bot.fetch_channel(mod_channel_id)
        if command := Command.get_or_none(Command.command == cmd):
            CommandText.create(text=text, command=command.id)
            if command.description != description:
                Command.update(description=description).where(Command.id == command.id).execute()
                self.bot.tree.get_command(command.command).description = description
                await self.bot.sync_slash_commands_for_guild(command.guild_id)
                await mod_channel.send(f"Beschreibung von Command `{cmd}` geändert zu `{description}`")
        else:
            if self.exists(cmd):
                return False
            command = Command.create(command=cmd, description=description, guild_id=guild_id)
            CommandText.create(text=text, command=command.id)
            await self.register_command(command)

        await mod_channel.send(f"[{cmd}] => [{text}] erfolgreich hinzugefügt.")
        return True

    async def remove_text(self, command, command_texts, id):
        command_text = list(command_texts)[id]
        command_text.delete_instance(recursive=True)
        if command.texts.count() == 0:
            await self.remove_command(command)

    async def remove_command(self, command: Command):
        await self.unregister_command(command)
        command.delete_instance(recursive=True)

    def exists(self, cmd):
        for command in self.bot.tree.get_commands():
            if command.name == cmd:
                return True

        return False

    async def init_commands(self):
        for command in Command.select():
            if command.texts.count() > 0:
                await self.register_command(command, sync=False)

    async def register_command(self, command: Command, sync: bool = True):
        @app_commands.command(name=command.command, description=command.description)
        @app_commands.guild_only()
        @app_commands.describe(public="Zeige die Ausgabe des Commands öffentlich, für alle Mitglieder sichtbar.")
        async def process_command(interaction: Interaction, public: bool):
            await interaction.response.defer(ephemeral=not public)
            if cmd := Command.get_or_none(Command.command == interaction.command.name):
                texts = list(cmd.texts)
                if len(texts) > 0:
                    await interaction.edit_original_response(content=(random.choice(texts)).text)
                    return

            await interaction.edit_original_response(content="FEHLER! Command wurde nicht gefunden!")

        self.bot.tree.add_command(process_command)
        if sync:
            await self.bot.sync_slash_commands_for_guild(command.guild_id)

    async def unregister_command(self, command: Command):
        self.bot.tree.remove_command(command.command)
        await self.bot.sync_slash_commands_for_guild(command.guild_id)


async def setup(bot: commands.Bot) -> None:
    text_commands = TextCommands(bot)
    await bot.add_cog(text_commands)
    await text_commands.init_commands()
    bot.add_view(TextCommandView(text_commands))
