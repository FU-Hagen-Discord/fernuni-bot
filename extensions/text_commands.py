import json
import os
import random
import re

import discord
from discord import Interaction, app_commands
from discord.app_commands import Group
from discord.ext import commands

import utils


@app_commands.guild_only()
class TextCommands(commands.GroupCog, name="commands", description="Text Commands auflisten und verwalten"):
    def __init__(self, bot):
        self.bot = bot
        self.text_commands = {}
        self.cmd_file = os.getenv("DISCORD_TEXT_COMMANDS_FILE")
        self.mod_channel_id = int(os.getenv("DISCORD_SUPPORT_CHANNEL"))
        self.load_text_commands()

    def load_text_commands(self):
        """ Loads all appointments from APPOINTMENTS_FILE """

        text_commands_file = open(self.cmd_file, mode='r')
        self.text_commands = json.load(text_commands_file)

    def save_text_commands(self):
        text_commands_file = open(self.cmd_file, mode='w')
        json.dump(self.text_commands, text_commands_file)

    @app_commands.command(name="list", description="Listet die Text Commands dieses Servers auf.")
    @app_commands.describe(cmd="Command für den die Texte ausgegeben werden sollen.")
    @app_commands.guild_only()
    async def cmd_list(self, interaction: Interaction, cmd: str = None):
        await self.list_commands(interaction, cmd=cmd[1:] if cmd and cmd[0] == "/" else cmd)

    @app_commands.command(name="add",
                          description="Ein neues Text Command hinzufügen, oder zu einem bestehenden einen weiteren text hinzufügen.")
    @app_commands.describe(cmd="Command. Bsp: \"link\" für das Command \"/link\".",
                           text="Text, der bei Benutzung des Commands ausgegeben werden soll.",
                           description="Beschreibung des Commands, die bei Benutzung angezeigt wird. Wird nur übernommen, bei neuen Commands.")
    async def cmd_add(self, interaction: Interaction, cmd: str, text: str, description: str):
        await interaction.response.defer(ephemeral=True)
        if not re.match(r"^[a-z0-9äöü]+(-[a-z0-9äöü]+)*$", cmd):
            await interaction.edit_original_response(
                content="Ein Command darf nur aus Kleinbuchstaben und Zahlen bestehen, die durch Bindestriche getrennt werden können.")
            return

        if utils.is_mod(interaction.user):
            if await self.add_command(cmd, text, description, interaction.guild_id):
                await interaction.edit_original_response(content="Dein Command wurde erfolgreich hinzugefügt!")
            else:
                await interaction.edit_original_response(
                    content="Das Command, dass du hinzufügen möchtest existiert bereits.")
        else:
            await self.suggest_command(cmd, text, description)
            await interaction.edit_original_response(content="Dein Vorschlag wurde den Mods zur Genehmigung vorgelegt.")

    @app_commands.command(name="edit", description="Bearbeite bestehende Text Commands")
    @app_commands.describe(cmd="Command, dass du bearbeiten möchtest", id="ID des zu bearbeitenden Texts",
                           text="Neuer Text, der statt des alten ausgegeben werden soll.")
    @app_commands.checks.has_role("Mod")
    async def cmd_edit(self, interaction: Interaction, cmd: str, id: int, text: str):
        await interaction.response.defer(ephemeral=True)

        if command := self.text_commands.get(cmd):
            texts = command.get('data')
            if 0 <= id < len(texts):
                texts[id] = text
                await interaction.edit_original_response(
                    content=f"Text {id} für Command {cmd} wurde erfolgreich geändert")
                self.save_text_commands()
            else:
                await interaction.edit_original_response(content=f"Ungültiger Index")
        else:
            await interaction.edit_original_response(content=f"Command {cmd} nicht vorhanden!")

    @app_commands.command(name="remove",
                          description="Entferne ein gesamtes Command oder einen einzelnen Text von einem Command.")
    @app_commands.describe(cmd="Command, dass du entfernen möchtest, oder von dem du einen Text entfernen möchtest.",
                           id="ID des zu entfernenden Texts.")
    @app_commands.checks.has_role("Mod")
    async def cmd_command_remove(self, interaction: Interaction, cmd: str, id: int = None):
        await interaction.response.defer(ephemeral=True)

        if command := self.text_commands.get(cmd):
            texts = command.get('data')
            if id is None or (len(texts) < 2 and id == 0):
                if cmd in self.text_commands:
                    self.text_commands.pop(cmd)
                    await interaction.edit_original_response(content="Text Command {cmd} wurde erfolgreich entfernt.")
                    self.save_text_commands()
                    self.bot.tree.remove_command(cmd)
                    await self.bot.sync_slash_commands_for_guild(interaction.guild_id)
                else:
                    await interaction.edit_original_response(content="Text Command {cmd} nicht vorhanden!")
            else:
                if 0 <= id < len(texts):  # schließt Aufrufe von Indizen aus, die außerhalb des Felds wären
                    del texts[id]
                    await interaction.edit_original_response(
                        content=f"Text {id} für Command {cmd} wurde erfolgreich entfernt")

                    self.save_text_commands()
                else:
                    await interaction.edit_original_response(content=f"Ungültiger Index")



        else:
            await interaction.edit_original_response(content=f"Command {cmd} nicht vorhanden!")

    async def list_commands(self, interaction: Interaction, cmd=None):
        await interaction.response.defer(ephemeral=True)

        if cmd and not self.text_commands.get(cmd):
            await interaction.edit_original_response(content=f"Es tut mir leid, für `/{cmd}` habe ich keine Texte "
                                                             f"hinterlegt, die ich dir anzeigen kann. Dies kann "
                                                             f"entweder daran liegen, dass dies kein gültiges Command "
                                                             f"ist, oder es handelt sich hierbei nicht um ein Command, "
                                                             f"dass nur Texte ausgibt.")
            return
        commands = await self.bot.get_slash_commands_for_guild(interaction.guild_id, command=cmd)

        msg = "**__Verfügbare Texte für: __**\n" if cmd else "**__Verfügbare Commands: __**\n"
        msg += "_\* hierbei handelt es s ich um ein Text Command, also einem Command, bei dem zufällig einer der " \
               "hinterlegten Texte ausgegeben wird. Über den optionalen Parameter `cmd` kannst du dir die hinterlegten " \
               "Texte zu diesem Command ausgeben lassen.\n\n_"
        for command in commands:
            text_command = self.text_commands.get(command.name)
            if command.default_permissions and interaction.permissions.value & command.default_permissions.value == 0:
                continue
            if isinstance(command, Group):
                msg += f"**{command.name}**: *{command.description}*\n"
                for c in command.commands:
                    msg += f"    `/{command.name} {c.name}`: *{c.description}*\n"
                msg += "\n"
            else:
                if text_command:
                    msg += f"`/{command.name}`\*: *{command.description}*\n"
                    if cmd:
                        for i, text in enumerate(text_command["data"]):
                            msg += f"`{i}`: {text}\n"
                else:
                    msg += f"`/{command.name}`: *{command.description}*\n"
                msg += "\n"

        await interaction.edit_original_response(content=msg)

    async def add_command(self, cmd: str, text: str, description: str, guild_id: int):
        mod_channel = await self.bot.fetch_channel(self.mod_channel_id)
        if command := self.text_commands.get(cmd):
            command["data"].append(text)
        else:
            if self.exists(cmd):
                return False
            self.text_commands[cmd] = {"description": description, "data": [text]}
            await self.register_command(cmd, description, guild_id=guild_id)

        await mod_channel.send(f"[{cmd}] => [{text}] erfolgreich hinzugefügt.")
        self.save_text_commands()
        return True

    async def suggest_command(self, cmd: str, text: str, description: str):
        mod_channel = await self.bot.fetch_channel(self.mod_channel_id)
        command = self.text_commands.get(cmd)
        title = "Vorschlag für neuen Command Text" if command else "Vorschlag für neues Command"

        embed = discord.Embed(title=title,
                              description=f"👍 um den Vorschlag anzunehmen\n"
                                          f"👎 um den Vorschlag abzulehnen")
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Command", value=f'{cmd}', inline=False)
        embed.add_field(name="Text", value=f'{text}', inline=False)
        if not command:
            embed.add_field(name="Beschreibung", value=description, inline=False)

        message = await mod_channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")

    def exists(self, cmd):
        for command in self.bot.tree.get_commands():
            if command.name == cmd:
                return True

        return False

    async def register_command(self, cmd: str, description: str, guild_id: int = 0, sync: bool = True):
        @app_commands.command(name=cmd, description=description)
        @app_commands.guild_only()
        @app_commands.describe(public="Zeige die Ausgabe des Commands öffentlich, für alle Mitglieder sichtbar.")
        async def process_command(interaction: Interaction, public: bool):
            await interaction.response.defer(ephemeral=not public)
            if command := self.text_commands.get(interaction.command.name):
                texts = command["data"]
                if len(texts) > 0:
                    await interaction.edit_original_response(content=(random.choice(texts)))
                    return

            await interaction.edit_original_response(content="FEHLER! Command wurde nicht gefunden!")

        self.bot.tree.add_command(process_command)
        if sync:
            await self.bot.sync_slash_commands_for_guild(guild_id)

    async def handle_command_reaction(self, message, approved=True):
        embed = message.embeds[0]
        fields = {field.name: field.value for field in embed.fields}
        cmd = fields.get("Command")
        text = fields.get("Text")
        description = fields.get("Beschreibung")

        if approved:
            await self.add_command(cmd, text, description, message.guild.id)
        await message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.emoji.name in ["👍", "👎"] and payload.channel_id == self.mod_channel_id:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds) > 0 and message.embeds[0].title in ["Vorschlag für neuen Command Text",
                                                                       "Vorschlag für neues Command"]:
                await self.handle_command_reaction(message, approved=(payload.emoji.name == "👍"))

    async def init_commands(self):
        for cmd, command in self.text_commands.items():
            if len(command["data"]) > 0:
                await self.register_command(cmd, command["description"], sync=False)


async def setup(bot: commands.Bot) -> None:
    text_commands = TextCommands(bot)
    await bot.add_cog(text_commands)
    await text_commands.init_commands()
