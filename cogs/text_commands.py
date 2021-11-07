import json
import os
import random
import re

import disnake
from disnake.ext import commands

import utils
from cogs.help import text_command_help, help, handle_error, remove_help_for, help_category


@help_category("textcommands", "Text-Kommandos", "", "Alle Werkzeuge zum Anlegen und Verwalten von Textkommandos.")
class TextCommands(commands.Cog):
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
        for cmd in self.text_commands:
            help_for_cmd = self.text_commands[cmd].get('help')

            if not help_for_cmd:
                continue

            brief = help_for_cmd.get('brief')
            category = help_for_cmd.get('category')
            if not brief:
                text_command_help(cmd)
                continue

            text_command_help(cmd, brief=brief, category=category)

    def save_text_commands(self):
        text_commands_file = open(self.cmd_file, mode='w')
        json.dump(self.text_commands, text_commands_file)

    @commands.group(name="commands")
    async def cmd_commands(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Fehlerhafte Nutzung von `!commands`. "
                           "Bitte benutze `!help` um herauszufinden, wie dieses Kommando benutzt wird.")

    @help(
        category="textcommands",
        brief="Listet alle verfügbaren Text-Commands auf oder die Texte, die zu einem Text-Command hinterlegt sind.",
        syntax="!commands list <cmd?>",
        example="!commands list !motivation",
        description="Gibt bei Angabe eines Kommandos (optionaler Parameter cmd) die Texte, die für dieses Kommandu hinterlegt sind.  ",
        parameters={
            "cmd": "*(optional)* Name des Kommandos, dessen Texte ausgegeben werden sollen."
        }
    )
    @cmd_commands.command(name="list")
    async def cmd_commands_list(self, ctx, cmd=None):
        await self.list_commands(ctx, cmd)

    @help(
        category="textcommands",
        brief="Schlägt ein Text-Kommando oder einen Text für ein bestehendes Text-Kommando vor.",
        syntax="!commands add <cmd> <text> <help_message?> <category?>",
        example="!command add !newcommand \"immer wenn newcommand aufgerufen wird wird das hier ausgegeben\" \"Hilfetext zu diesem Kommando\"",
        description="Ein Text-Kommando ist ein Kommando welches über !<name des textkommandos> aufgerufen werden kann und dann zufällig einen der hinterlegten Texte ausgibt.",
        parameters={
            "cmd": "Name des anzulegenden Kommandos (z. B. !horoskop). ",
            "text": "in Anführungszeichen eingeschlossene Textnachricht, die ausgegeben werden soll, wenn das Kommando aufgerufen wird (z. B. \"Wassermann: Findet diese Woche wahrscheinlich seinen Dreizack wieder.\").",
            "help_message": "*(optional)* Die Hilfenachricht, die bei `!help` für dieses Kommando erscheinen soll (in Anführungszeichen). ",
            "category": "*(optional)* gibt die Kategorie an in der das Kommando angezeigt werden soll. "
        }
    )
    @cmd_commands.command(name="add")
    async def cmd_commands_add(self, ctx, cmd, text, help_message=None, category=None):
        if utils.is_mod(ctx):
            await self.add_command(cmd, text, help_message=help_message, category=category)
        else:
            await self.suggest_command(ctx, cmd, text, help_message=help_message, category=category)

    @help(
        category="textcommands",
        brief="Ändert den Text eines Text-Kommandos.",
        syntax="!commands edit <cmd> <id> <text>",
        example="!command edit !command 1 \"Neuer Text\"",
        description="Ändert den Text eines Text-Kommandos an angegebenem Index.",
        parameters={
            "cmd": "Name des anzulegenden Kommandos (z. B. !horoskop). ",
            "id": "Index des zu ändernden Texts.",
            "text": "in Anführungszeichen eingeschlossene Textnachricht, die ausgegeben werden soll, wenn das Kommando aufgerufen wird (z. B. \"Wassermann: Findet diese Woche wahrscheinlich seinen Dreizack wieder.\").",
        },
        mod=True
    )
    @cmd_commands.command(name="edit")
    @commands.check(utils.is_mod)
    async def cmd_command_edit(self, ctx, cmd, id, text):
        texts = self.text_commands.get(cmd).get('data')

        if texts:
            i = int(id)
            if 0 <= i < len(texts):
                texts[i] = text
                await ctx.send(f"Text {i} für Command {cmd} wurde erfolgreich geändert")
                self.save_text_commands()
            else:
                await ctx.send(f"Ungültiger Index")
        else:
            await ctx.send("Command {cmd} nicht vorhanden!")

    @help(
        category="textcommands",
        brief="Entfernt einen Text oder ein gesamtes Text-Kommando.",
        syntax="!commands remove <cmd> <id?>",
        example="!command remove !command 0",
        description="Entfernt den Text des angegebenen Text-Kommandos an entsprechendem Index. War das der einzige Text für dieses Text-Kommando, wird das gesamte Kommando entfernt. Wird kein Index übergeben, so wird ebenfalls das gesamte Text-Kommando entfernt.",
        parameters={
            "cmd": "Name des zu entfernenden Kommandos (z. B. !horoskop). ",
            "id": "*(optional)* Id des zu löschenden Texts"
        },
        mod=True
    )
    @cmd_commands.command(name="remove")
    @commands.check(utils.is_mod)
    async def cmd_command_remove(self, ctx, cmd, id=None):
        texts = self.text_commands.get(cmd).get('data')

        if texts:
            if id:  # checkt erst, ob man lediglich einen Eintrag (und nicht das ganze Command) löschen möchte
                i = int(id)
                if 0 <= i < len(texts):  # schließt Aufrufe von Indizen aus, die außerhalb des Felds wären
                    del texts[i]
                    await ctx.send(f"Text {i} für Command {cmd} wurde erfolgreich entfernt")

                    if len(texts) == 0:
                        self.text_commands.pop(cmd)

                    self.save_text_commands()
                else:
                    await ctx.send(f"Ungültiger Index")
            else:  # jetzt kommt man zum vollständigen command removal (ursprünglich "remove-text-command")
                # Hier könnte eine Bestätigung angefordert werden (Möchtest du wirklich das Command vollständig löschen? 👍👎)
                if cmd in self.text_commands:
                    self.text_commands.pop(cmd)
                    remove_help_for(re.sub(r"^!", "", cmd))
                    await ctx.send(f"Text Command {cmd} wurde erfolgreich entfernt.")
                    self.save_text_commands()
                else:
                    await ctx.send(f"Text Command {cmd} nicht vorhanden!")
        else:
            await ctx.send("Command {cmd} nicht vorhanden!")

    @cmd_commands.command(name="edit-help")
    @commands.check(utils.is_mod)
    async def cmd_command_edit_help(self, ctx, cmd, help_message):
        help_object = None
        try:
            cmd = re.sub(r"^!*", "!", cmd)
            help_object = self.text_commands.get(cmd).get('help')
        except:
            pass

        if not help_object:
            self.text_commands[cmd]['help'] = {}
            help_object = self.text_commands[cmd]['help']

        help_object['brief'] = help_message
        text_command_help(cmd, brief=help_message, category=help_object.get('category'))
        self.save_text_commands()

        await ctx.send(f"[{cmd}] => Hilfe [{help_message}] erfolgreich hinzugefügt.")

    @cmd_commands.command(name="edit-category")
    @commands.check(utils.is_mod)
    async def cmd_command_edit_category(self, ctx, cmd, category):
        help_object = None
        try:
            help_object = self.text_commands.get(re.sub("^!*", "!", cmd)).get('help')
        except:
            pass

        if not help_object:
            help_object = {}

        help_object['category'] = category
        text_command_help(cmd, category=category, brief=help_object.get('brief'))
        self.save_text_commands()

        await ctx.send(f"[{cmd}] => Erfolgreich auf Kategorie [{category}] geändert.")

    async def list_commands(self, ctx, cmd=None):
        if cmd and not self.text_commands.get(cmd):
            await ctx.send(f"{cmd} ist kein verfügbares Text-Command")
            return

        answer = f"Text Commands:\n" if cmd is None else f"Für {cmd} hinterlegte Texte:\n"
        cmd_list = list(self.text_commands.keys()) if cmd is None else self.text_commands.get(cmd).get('data')

        for i in range(len(cmd_list)):
            text = cmd_list[i]
            if len(answer) + len(text) > 2000:
                await ctx.send(answer)
                answer = f""

            answer += f"{i}: {text}\n"

        await ctx.send(answer)

    async def add_command(self, cmd, text, help_message=None, category=None):
        mod_channel = await self.bot.fetch_channel(self.mod_channel_id)
        command = self.get_or_init_command(cmd)
        texts = command.get("data")
        texts.append(text)

        if help_message and not command.get("help"):
            command["help"] = {"brief": help_message}
            if category:
                command.get("help")["category"] = category

        await mod_channel.send(f"[{cmd}] => [{text}] erfolgreich hinzugefügt.")

        self.save_text_commands()

    async def suggest_command(self, ctx, cmd, text, help_message=None, category=None):
        mod_channel = await self.bot.fetch_channel(self.mod_channel_id)
        command = self.text_commands.get(cmd)
        title = "Vorschlag für neuen Command Text" if command else "Vorschlag für neues Command"

        embed = disnake.Embed(title=title,
                              description=f"<@!{ctx.author.id}> hat folgenden Vorschlag eingereicht.\n"
                                          f"👍 um den Vorschlag anzunehmen\n"
                                          f"👎 um den Vorschlag abzulehnen")
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Command", value=f'{cmd}', inline=False)
        embed.add_field(name="Text", value=f'{text}', inline=False)
        if help_message:
            embed.add_field(name="Hilfetext", value=f'{help_message}', inline=False)
        if category:
            embed.add_field(name="Kategorie", value=f'{category}', inline=False)

        message = await mod_channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await utils.send_dm(ctx.author,
                            "Dein Vorschlag wurde den Mods zur Genehmigung vorgelegt. "
                            "Sobald darüber entschieden wurde, erhältst du eine Benachrichtigung.")

    def get_or_init_command(self, cmd):
        if command := self.text_commands.get(cmd):
            return command

        self.text_commands[cmd] = {"data": []}
        return self.text_commands.get(cmd)

    async def handle_command_reaction(self, message, approved=True):
        embed = message.embeds[0]
        fields = {field.name: field.value for field in embed.fields}
        cmd = fields.get("Command")
        text = fields.get("Text")
        help_message = fields.get("Hilfetext")
        category = fields.get("Kategorie")
        member = await message.guild.fetch_member(embed.description[3:21])

        if approved:
            await self.add_command(cmd, text, help_message=help_message, category=category)
            await utils.send_dm(member,
                                f"Herzlichen Glückwunsch, dein Vorschlag für {cmd} wurde angenommen:\n{text}")
        else:
            await utils.send_dm(member,
                                f"Vielen Dank, dass du dir Gedanken darüber machst, wie man Boty mit neuen Textkommandos noch nützlicher für alle machen kann.\n" \
                                f"Es können allerdings nicht alle Einreichungen angenommen werden, weswegen dein Vorschlag für {cmd} leider abgelehnt wurde:\n{text}\n" \
                                f"Eine Vertreterin des Mod-Teams wird sich in Kürze mit dir in Verbindung setzen und dir erklären, was die Beweggründe der Ablehnung sind.")
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

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)

    @commands.Cog.listener(name="on_message")
    async def process_text_commands(self, message):
        if message.author == self.bot.user:
            return

        cmd = message.content.split(" ")[0]
        cmd_object = self.text_commands.get(cmd)
        if cmd_object:
            texts = cmd_object.get('data')
            if texts:
                await message.channel.send(random.choice(texts))
