import copy
import enum
import json
import os
import re
import time
from enum import Enum

import discord
from discord import InteractionMessage, app_commands, Interaction
from discord.ext import commands
from discord.ui import Button

import utils

"""
  Umgebungsvariablen:
  DISCORD_LEARNINGGROUPS_OPEN - Kategorie-ID der offenen Lerngruppen
  DISCORD_LEARNINGGROUPS_CLOSE - Kategorie-ID der geschlossenen Lerngruppen
  DISCORD_LEARNINGGROUPS_PRIVATE - Kategorie-ID der privaten Lerngruppen
  DISCORD_LEARNINGGROUPS_ARCHIVE - Kategorie-ID der archivierten Lerngruppen
  DISCORD_LEARNINGGROUPS_REQUEST - ID des Kanals, in dem Anfragen, die über den Bot gestellt wurden, eingetragen werden
  DISCORD_LEARNINGGROUPS_INFO - ID des Kanals, in dem die Lerngruppen-Informationen gepostet/aktualisert werden
  DISCORD_LEARNINGGROUPS_FILE - Name der Datei mit Verwaltungsdaten der Lerngruppen (minimaler Inhalt: {"requested": {},"groups": {}})
  DISCORD_LEARNINGGROUPS_COURSE_FILE - Name der Datei welche die Kursnamen für die Lerngruppen-Informationen enthält (minimaler Inhalt: {})
  DISCORD_MOD_ROLE - ID der Moderations-Rolle, die erweiterte Lerngruppen-Aktionen ausführen darf
"""

LG_OPEN_SYMBOL = f'🌲'
LG_CLOSE_SYMBOL = f'🛑'
LG_PRIVATE_SYMBOL = f'🚪'
LG_LISTED_SYMBOL = f'📖'


class LearningGroupState(enum.Enum):
    open = "open"
    private = "private"


class GroupState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRIVATE = "PRIVATE"
    ARCHIVED = "ARCHIVED"
    REMOVED = "REMOVED"


@app_commands.guild_only()
class LearningGroups(commands.GroupCog, name="lg", description="Lerngruppenverwaltung."):
    def __init__(self, bot):
        self.bot = bot
        # ratelimit 2 in 10 minutes (305 * 2 = 610 = 10 minutes and 10 seconds)
        self.rename_ratelimit = 305
        self.msg_max_len = 1900

        self.categories = {
            GroupState.OPEN: os.getenv('DISCORD_LEARNINGGROUPS_OPEN'),
            GroupState.CLOSED: os.getenv('DISCORD_LEARNINGGROUPS_CLOSE'),
            GroupState.PRIVATE: os.getenv('DISCORD_LEARNINGGROUPS_PRIVATE'),
            GroupState.ARCHIVED: os.getenv('DISCORD_LEARNINGGROUPS_ARCHIVE')
        }
        self.symbols = {
            GroupState.OPEN: LG_OPEN_SYMBOL,
            GroupState.CLOSED: LG_CLOSE_SYMBOL,
            GroupState.PRIVATE: LG_PRIVATE_SYMBOL
        }
        self.channel_request = os.getenv('DISCORD_LEARNINGGROUPS_REQUEST')
        self.channel_info = os.getenv('DISCORD_LEARNINGGROUPS_INFO')
        self.group_file = os.getenv('DISCORD_LEARNINGGROUPS_FILE')
        self.header_file = os.getenv('DISCORD_LEARNINGGROUPS_COURSE_FILE')
        self.support_channel = os.getenv('DISCORD_SUPPORT_CHANNEL')
        self.mod_role = os.getenv("DISCORD_MOD_ROLE")
        self.guild_id = os.getenv("DISCORD_GUILD")
        self.groups = {}  # organizer and learninggroup-member ids
        self.channels = {}  # complete channel configs
        self.header = {}  # headlines for status message
        self.load_groups()
        self.load_header()

    @commands.Cog.listener()
    async def on_button_click(self, interaction: InteractionMessage):
        button: Button = interaction.component

        if button.custom_id == "learninggroups:group_yes":
            await self.on_group_request(True, button, interaction)
        elif button.custom_id == "learninggroups:group_no":
            await self.on_group_request(False, button, interaction)
        elif button.custom_id == "learninggroups:join_yes":
            await self.on_join_request(True, button, interaction)
        elif button.custom_id == "learninggroups:join_no":
            await self.on_join_request(False, button, interaction)

    @commands.Cog.listener(name="on_ready")
    async def on_ready(self):
        await self.update_channels()

    def load_header(self):
        file = open(self.header_file, mode='r')
        self.header = json.load(file)

    def save_header(self):
        file = open(self.header_file, mode='w')
        json.dump(self.header, file)

    def load_groups(self):
        group_file = open(self.group_file, mode='r')
        self.groups = json.load(group_file)
        if not self.groups.get("groups"):
            self.groups['groups'] = {}
        if not self.groups.get("requested"):
            self.groups['requested'] = {}
        if not self.groups.get("messageids"):
            self.groups['messageids'] = []

        for _, group in self.groups['requested'].items():
            group["state"] = GroupState[group["state"]]

    async def save_groups(self):
        await self.update_channels()
        group_file = open(self.group_file, mode='w')

        groups = copy.deepcopy(self.groups)

        for _, group in groups['requested'].items():
            group["state"] = group["state"].name
        json.dump(groups, group_file)

    def arg_state_to_group_state(self, state: LearningGroupState):
        if state == LearningGroupState.open:
            return GroupState.OPEN
        if state == LearningGroupState.private:
            return GroupState.PRIVATE
        return None

    def is_request_organizer(self, request, member):
        return request["organizer_id"] == member.id

    def is_group_organizer(self, channel, member):
        channel_config = self.groups["groups"].get(str(channel.id))
        if channel_config:
            return channel_config["organizer_id"] == member.id
        return False

    def is_mod(self, member):
        roles = member.roles
        for role in roles:
            if role.id == int(self.mod_role):
                return True

        return False

    def is_group_request_message(self, message):
        return len(message.embeds) > 0 and message.embeds[0].title == "Lerngruppenanfrage!"

    def is_channel_config_valid(self, channel_config, command):
        if channel_config['state'] is None:
            return False, f"Fehler! Bitte gib an ob die Gruppe **offen** (**open**) **geschlossen** (**closed**) oder **privat** (**private**) ist. Gib `!help {command}` für Details ein."
        if not re.match(r"^(sose|wise)[0-9]{2}$", channel_config['semester']):
            return False, f"Fehler! Das Semester muss mit **sose** oder **wise** angegeben werden gefolgt von der **zweistelligen Jahreszahl**. Gib `!help {command}` für Details ein."
        return True, ""

    async def check_rename_rate_limit(self, channel_config):
        if channel_config.get("last_rename") is None:
            return False
        now = int(time.time())
        seconds = channel_config["last_rename"] + self.rename_ratelimit - now
        if seconds > 0:
            channel = await self.bot.fetch_channel(int(channel_config["channel_id"]))
            await channel.send(
                f"Discord schränkt die Anzahl der Aufrufe für manche Funktionen ein, daher kannst du diese Aktion erst wieder in {seconds} Sekunden ausführen.")
        return seconds > 0

    async def category_of_channel(self, state: GroupState):
        category_to_fetch = self.categories[state]
        category = await self.bot.fetch_channel(category_to_fetch)
        return category

    def full_channel_name(self, channel_config):
        return (f"{self.symbols[channel_config['state']]}"
                f"{channel_config['course']}-{channel_config['name']}-{channel_config['semester']}"
                f"{LG_LISTED_SYMBOL if channel_config['is_listed'] else ''}")

    async def update_statusmessage(self):
        info_message_ids = self.groups.get("messageids")
        channel = await self.bot.fetch_channel(int(self.channel_info))

        for info_message_id in info_message_ids:
            message = await channel.fetch_message(info_message_id)
            await message.delete()

        info_message_ids = []

        msg = f"**Lerngruppen**\n\n"
        course_msg = ""
        sorted_channels = sorted(self.channels.values(
        ), key=lambda channel: f"{channel['course']}-{channel['name']}")
        open_channels = [channel for channel in sorted_channels if channel['state'] in [GroupState.OPEN]
                         or channel['is_listed']]
        courseheader = None
        no_headers = []
        for lg_channel in open_channels:

            if lg_channel['course'] != courseheader:
                if len(msg) + len(course_msg) > self.msg_max_len:
                    message = await channel.send(msg)
                    info_message_ids.append(message.id)
                    msg = course_msg
                    course_msg = ""
                else:
                    msg += course_msg
                    course_msg = ""
                header = self.header.get(lg_channel['course'])
                if header:
                    course_msg += f"**{header}**\n"
                else:
                    course_msg += f"**{lg_channel['course']} - -------------------------------------**\n"
                    no_headers.append(lg_channel['course'])
                courseheader = lg_channel['course']

            groupchannel = await self.bot.fetch_channel(int(lg_channel['channel_id']))
            course_msg += f"    {groupchannel.mention}"

            if lg_channel['is_listed'] and lg_channel['state'] == GroupState.PRIVATE:
                group_config = self.groups["groups"].get(lg_channel['channel_id'])
                if group_config:
                    user = await self.bot.fetch_user(group_config['organizer_id'])
                    if user:
                        course_msg += f" **@{user.name}#{user.discriminator}**"
                course_msg += f"\n       **↳** `!lg join {groupchannel.id}`"
            course_msg += "\n"

        msg += course_msg
        message = await channel.send(msg)
        if len(no_headers) > 0:
            support_channel = await self.bot.fetch_channel(int(self.support_channel))
            if support_channel:
                await support_channel.send(
                    f"In der Lerngruppenübersicht fehlen noch Überschriften für die folgenden Kurse: **{', '.join(no_headers)}**")
        info_message_ids.append(message.id)
        self.groups["messageids"] = info_message_ids
        await self.save_groups()

    async def archive(self, channel):
        group_config = self.groups["groups"].get(str(channel.id))
        if not group_config:
            await channel.send("Das ist kein Lerngruppenkanal.")
            return
        category = await self.bot.fetch_channel(self.categories[GroupState.ARCHIVED])
        await self.move_channel(channel, category)
        await channel.edit(name=f"archiv-${channel.name[1:]}")
        await self.update_permissions(channel)
        await self.remove_group(channel)
        await self.update_statusmessage()

    async def set_channel_state(self, channel, state: GroupState = None):
        channel_config = self.channels[str(channel.id)]
        if await self.check_rename_rate_limit(channel_config):
            return False  # prevent api requests when ratelimited

        if state is not None:
            old_state = channel_config["state"]
            if old_state == state:
                return False  # prevent api requests when nothing has changed
            channel_config["state"] = state
            await self.alter_channel(channel, channel_config)
            return True

    async def set_channel_listing(self, channel, is_listed):
        channel_config = self.channels[str(channel.id)]
        if await self.check_rename_rate_limit(channel_config):
            return False  # prevent api requests when ratelimited
        if channel_config["state"] in [GroupState.CLOSED, GroupState.PRIVATE]:
            was_listed = channel_config["is_listed"]
            if was_listed == is_listed:
                return False  # prevent api requests when nothing has changed
            channel_config["is_listed"] = is_listed
            await self.alter_channel(channel, channel_config)
            return True

    async def alter_channel(self, channel, channel_config):
        self.groups["groups"][str(channel.id)]["last_rename"] = int(time.time())
        await channel.edit(name=self.full_channel_name(channel_config))
        category = await self.category_of_channel(channel_config["state"])
        await self.move_channel(channel, category,
                                sync=True if channel_config["state"] in [GroupState.OPEN, GroupState.CLOSED] else False)
        await self.save_groups()
        await self.update_statusmessage()
        return True

    async def set_channel_name(self, channel, name):
        channel_config = self.channels[str(channel.id)]

        if await self.check_rename_rate_limit(channel_config):
            return  # prevent api requests when ratelimited

        self.groups["groups"][str(channel.id)]["last_rename"] = int(time.time())
        channel_config["name"] = name

        await channel.edit(name=self.full_channel_name(channel_config))
        await self.save_groups()
        await self.update_statusmessage()

    async def move_channel(self, channel, category, sync=True):
        for sortchannel in category.text_channels:
            if sortchannel.name[1:] > channel.name[1:]:
                await channel.move(category=category, before=sortchannel, sync_permissions=sync)
                return
        await channel.move(category=category, sync_permissions=sync, end=True)

    async def add_requested_group_channel(self, message, direct=False):
        requested_channel_config = self.groups["requested"].get(str(message.id))

        category = await self.category_of_channel(requested_channel_config["state"])
        full_channel_name = self.full_channel_name(requested_channel_config)
        channel = await category.create_text_channel(full_channel_name)
        await self.move_channel(channel, category, False)
        user = await self.bot.fetch_user(requested_channel_config["organizer_id"])

        await channel.send(f":wave: <@!{user.id}>, hier ist deine neue Lerngruppe.\n"
                           "Es gibt offene und private Lerngruppen. Eine offene Lerngruppe ist für jeden sichtbar "
                           "und jeder kann darin schreiben. Eine private Lerngruppe ist unsichtbar und auf eine "
                           "Gruppe an Kommilitoninnen beschränkt."
                           "```"
                           "Funktionen für Lerngruppenorganisatorinnen:\n"
                           "!lg addmember <@newmember>: Fügt ein Mitglied zur Lerngruppe hinzu.\n"
                           "!lg organizer <@neworganizer>: Ändert die Organisatorin der Lerngruppe auf @neworganizer.\n"
                           "!lg open: Öffnet eine Lerngruppe.\n"
                           "!lg close: Schließt eine Lerngruppe.\n"
                           "!lg private: Stellt die Lerngruppe auf privat.\n"
                           "!lg show: Zeigt eine private oder geschlossene Lerngruppe in der Lerngruppenliste an.\n"
                           "!lg hide: Entfernt eine private oder geschlossene Lerngruppe aus der Lerngruppenliste.\n"
                           "!lg kick <@user>: Schließt eine Benutzerin von der Lerngruppe aus.\n"
                           "\nKommandos für alle:\n"
                           "!lg id: Zeigt die ID der Lerngruppe an mit der andere Kommilitoninnen beitreten können.\n"
                           "!lg members: Zeigt die Mitglieder der Lerngruppe an.\n"
                           "!lg organizer: Zeigt die Organisatorin der Lerngruppe an.\n"
                           "!lg leave: Du verlässt die Lerngruppe.\n"
                           "!lg join: Anfrage, um der Lerngruppe beizutreten.\n"
                           "\nMit dem nachfolgenden Kommando kann eine Kommilitonin darum "
                           "bitten in die Lerngruppe aufgenommen zu werden wenn die Gruppe privat ist.\n"
                           f"!lg join {channel.id}"
                           "\n(Manche Kommandos werden von Discord eingeschränkt und können nur einmal alle 5 Minuten ausgeführt werden.)"
                           "```"
                           )
        self.groups["groups"][str(channel.id)] = {
            "organizer_id": requested_channel_config["organizer_id"],
            "last_rename": int(time.time())
        }

        await self.remove_group_request(message)
        if not direct:
            await message.delete()

        await self.save_groups()
        await self.update_statusmessage()
        if requested_channel_config["state"] is GroupState.PRIVATE:
            await self.update_permissions(channel)

    async def remove_group_request(self, message):
        del self.groups["requested"][str(message.id)]
        await self.save_groups()

    async def remove_group(self, channel):
        del self.groups["groups"][str(channel.id)]
        await self.save_groups()

    def channel_to_channel_config(self, channel):
        cid = str(channel.id)
        is_listed = channel.name[-1] == LG_LISTED_SYMBOL
        result = re.match(r"([0-9]+)-(.*)-([a-z0-9]+)$", channel.name[1:] if not is_listed else channel.name[1:-1])

        state = None
        if channel.name[0] == LG_OPEN_SYMBOL:
            state = GroupState.OPEN
        elif channel.name[0] == LG_CLOSE_SYMBOL:
            state = GroupState.CLOSED
        elif channel.name[0] == LG_PRIVATE_SYMBOL:
            state = GroupState.PRIVATE

        course, name, semester = result.group(1, 2, 3)

        channel_config = {"course": course, "name": name, "category": channel.category_id, "semester": semester,
                          "state": state, "is_listed": is_listed, "channel_id": cid}
        if self.groups["groups"].get(cid):
            channel_config.update(self.groups["groups"].get(cid))
        return channel_config

    async def update_channels(self):
        self.channels = {}
        for state in [GroupState.OPEN, GroupState.CLOSED, GroupState.PRIVATE]:
            category = await self.category_of_channel(state)

            for channel in category.text_channels:
                channel_config = self.channel_to_channel_config(channel)

                self.channels[str(channel.id)] = channel_config

    async def add_member_to_group(self, channel: discord.TextChannel, arg_member: discord.Member, send_message=True):
        group_config = self.groups["groups"].get(str(channel.id))
        if not group_config:
            await channel.send("Das ist kein Lerngruppenkanal.")
            return

        users = group_config.get("users")
        if not users:
            users = {}
        mid = str(arg_member.id)
        if not users.get(mid):
            users[mid] = True
            user = await self.bot.fetch_user(mid)
            if user and send_message:
                try:
                    await utils.send_dm(user, f"Du wurdest in die Lerngruppe <#{channel.id}> aufgenommen. "
                                              "Viel Spass beim gemeinsamen Lernen!\n"
                                              "Dieser Link führt dich direkt zum Lerngruppenkanal. "
                                              "Diese Nachricht kannst du in unserer Unterhaltung mit Rechtsklick anpinnen, "
                                              "wenn du möchtest.")
                except:
                    pass

        group_config["users"] = users

        await self.save_groups()

    async def remove_member_from_group(self, channel: discord.TextChannel, arg_member: discord.Member,
                                       send_message=True):
        group_config = self.groups["groups"].get(str(channel.id))
        if not group_config:
            await channel.send("Das ist kein Lerngruppenkanal.")
            return

        users = group_config.get("users")
        if not users:
            return
        mid = str(arg_member.id)
        if users.pop(mid, None):
            user = await self.bot.fetch_user(mid)
            if user and send_message:
                await utils.send_dm(user, f"Du wurdest aus der Lerngruppe {channel.name} entfernt.")

        await self.save_groups()

    async def update_permissions(self, channel):
        channel_config = self.channels[str(channel.id)]
        if channel_config.get("state") == GroupState.PRIVATE:
            overwrites = await self.overwrites(channel)
            await channel.edit(overwrites=overwrites)
        else:
            await channel.edit(sync_permissions=True)

    async def overwrites(self, channel):
        channel = await self.bot.fetch_channel(str(channel.id))
        group_config = self.groups["groups"].get(str(channel.id))
        guild = await self.bot.fetch_guild(int(self.guild_id))
        mods = guild.get_role(int(self.mod_role))

        overwrites = {
            mods: discord.PermissionOverwrite(read_messages=True),
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        if not group_config:
            return overwrites

        organizer = self.bot.get_user(group_config["organizer_id"])
        if not organizer:
            return overwrites

        overwrites[organizer] = discord.PermissionOverwrite(read_messages=True)
        users = group_config.get("users")
        if not users:
            return overwrites

        for userid in users.keys():
            user = await self.bot.fetch_user(userid)
            overwrites[user] = discord.PermissionOverwrite(read_messages=True)

        return overwrites

    @app_commands.command(name="update", description="Aktualisiert die Lerngruppenliste")
    @app_commands.checks.has_role("Mod")
    async def cmd_update(self, interaction: Interaction):
        await interaction.response.send_message("Update der Lerngruppenliste gestartet...")
        await self.update_channels()
        await self.update_statusmessage()
        await interaction.edit_original_response(content="Update der Lerngruppenliste abgeschlossen!")

    @app_commands.command(name="header",
                          description="Fügt einen Kurs als neue Überschrift in Botys Lerngruppen-Liste hinzu.")
    @app_commands.describe(
        course="Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
        name="Ein frei wählbarer Text (darf Leerzeichen enthalten).")
    @app_commands.checks.has_role("Mod")
    async def cmd_add_header(self, interaction: Interaction, course: int, name: str):
        await interaction.response.defer()

        self.header[course] = f"{course} - {name}"
        self.save_header()
        await self.update_statusmessage()
        await interaction.edit_original_response(content=f"Überschrift {name} für Kurs {course} hinzugefügt.")

    @app_commands.command(name="request", description="Stellt eine Anfrage für einen neuen Lerngruppenkanal.")
    @app_commands.describe(
        course="Nummer des Kurses, wie von der FernUni angegeben (ohne führende Nullen z. B. 1142).",
        name="Ein frei wählbarer Text ohne Leerzeichen.",
        semester="Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der zweistelligen Jahreszahl (z. B. sose22)",
        state="Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed) oder ob es sich um eine private Lerngruppe handelt (private).")
    async def cmd_request_group(self, interaction: Interaction, course: int, name: str, semester: str,
                                state: LearningGroupState):
        await interaction.response.defer(ephemeral=True)
        arg_semester = re.sub(r"[^wiseo0-9]", "", semester)
        state = self.arg_state_to_group_state(state)
        name = re.sub(r"[^A-Za-zäöüß0-9-]", "", name.lower().replace(" ", "-"))

        if len(arg_semester) == 8:
            arg_semester = f"{arg_semester[0:4]}{arg_semester[-2:]}"
        channel_config = {"organizer_id": interaction.user.id, "course": course, "name": name,
                          "semester": arg_semester,
                          "state": state, "is_listed": False}

        is_valid, error = self.is_channel_config_valid(channel_config, interaction.command.name)
        if not is_valid:
            await interaction.edit_original_response(content=error)
            return

        channel = await self.bot.fetch_channel(int(self.channel_request))
        channel_name = self.full_channel_name(channel_config)

        message = await utils.confirm(
            channel=channel,
            title="Lerngruppenanfrage",
            description=f"{interaction.user.mention} möchte gerne die Lerngruppe **#{channel_name}** eröffnen.",
            custom_prefix="learninggroups:group"
        )
        self.groups["requested"][str(message.id)] = channel_config
        await self.save_groups()
        await interaction.edit_original_response(content="Deine Lerngruppenanfrage wurde an die Moderatorinnen zur "
                                                         "Genehmigung weitergeleitet. Du erhältst eine Nachricht, "
                                                         "wenn über deine Anfrage entschieden wurde.")

    @app_commands.command(name="add",
                          description="Fügt einen Lerngruppenkanal hinzu. Der Name darf keine Leerzeichen enthalten.")
    @app_commands.describe(
        course="Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
        name="Ein frei wählbarer Text ohne Leerzeichen. Bindestriche sind zulässig.",
        semester="Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der zweistelligen Jahreszahl (z. B. sose22).",
        state="Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (private).",
        organizer="Die so erwähnte Benutzerin wird als Organisatorin der Lerngruppe eingesetzt.")
    @commands.check(utils.is_mod)
    async def cmd_add_group(self, interaction: Interaction, course: int, name: str, semester: str,
                            state: LearningGroupState, organizer: discord.Member):
        await interaction.response.defer(ephemeral=True)
        state = self.arg_state_to_group_state(state)
        channel_config = {"organizer_id": organizer.id, "course": course, "name": name,
                          "semester": semester,
                          "state": state, "is_listed": False}

        is_valid, error = await self.is_channel_config_valid(channel_config, interaction.command.name)
        if not is_valid:
            await interaction.edit_original_response(content=error)
            return

        self.groups["requested"][str(interaction.message.id)] = channel_config
        await self.save_groups()
        await self.add_requested_group_channel(interaction.message.id, direct=True)

    @app_commands.command(name="show", description="Zeigt einen privaten Lerngruppenkanal trotzdem in der Liste an.")
    async def cmd_show(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
            channel_config = self.channels[str(interaction.channel.id)]
            if channel_config:
                if channel_config.get("state") == GroupState.PRIVATE:
                    if await self.set_channel_listing(interaction.channel, True):
                        await interaction.edit_original_response(
                            content="Die Lerngruppe wird nun in der Lerngruppenliste angezeigt.")
                elif channel_config.get("state") == GroupState.OPEN:
                    await interaction.edit_original_response(
                        content="Nichts zu tun. Offene Lerngruppen werden sowieso in der Liste angezeigt.")
                elif channel_config.get("state") == GroupState.CLOSED:
                    await interaction.edit_original_response(
                        content="Möchtest du die Gruppen öffnen? Versuch's mit `!lg open`")

    @app_commands.command(name="hide", description="Versteckt einen privaten Lerngruppenkanal.")
    async def cmd_hide(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
            channel_config = self.channels[str(interaction.channel.id)]
            if channel_config:
                if channel_config.get("state") == GroupState.PRIVATE:
                    if await self.set_channel_listing(interaction.channel, False):
                        await interaction.edit_original_response(
                            content="Die Lerngruppe wird nun nicht mehr in der Lerngruppenliste angezeigt.")
                    return

                elif channel_config.get("state") == GroupState.OPEN:
                    await interaction.edit_original_response(
                        content="Offene Lerngruppen können nicht aus der Lerngruppenliste entfernt werden. "
                                "Führe `!lg private`, um diese auf privat zu schalten.")
                elif channel_config.get("state") == GroupState.CLOSED:
                    await interaction.edit_original_response(content=
                                                             "Wenn diese Gruppe privat werden soll, ist das Kommando das du brauchst: `!lg private`")

    @app_commands.command(name="debug", description="Irgendwelche Debug-Kacke")
    @app_commands.checks.has_role("Mod")
    async def cmd_debug(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        channel_config = self.channels[str(interaction.channel.id)]
        if not channel_config:
            await interaction.edit_original_response(content="None")
            return
        await interaction.edit_original_response(content=str(channel_config))

    @app_commands.command(name="open", description="Öffnet den Lerngruppenkanal, wenn du die Organisatorin bist.")
    async def cmd_open(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
            await self.set_channel_state(interaction.channel, state=GroupState.OPEN)
        await interaction.edit_original_response(content="Die Lerngruppe wurde geöffnet.")

    @app_commands.command(name="private",
                          description="Macht aus deiner Lerngruppe eine private Lerngruppe, wenn du die Organisatorin bist.")
    async def cmd_private(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
            if await self.set_channel_state(interaction.channel, state=GroupState.PRIVATE):
                await self.update_permissions(interaction.channel)
        await interaction.edit_original_response(content="Die Lerngruppe wurde geöffnet.")

    @app_commands.command(name="organizer", description="Bestimmt die Organisatorin eines Lerngruppenkanals.")
    @app_commands.describe(new_organizer="Die neue Organisatorin der Lerngruppe.")
    async def cmd_organizer(self, interaction: Interaction, new_organizer: discord.Member = None):
        await interaction.response.defer(defer=True)
        group_config = self.groups["groups"].get(str(interaction.channel.id))

        if not group_config:
            self.groups["groups"][str(interaction.channel.id)] = {}
            group_config = self.groups["groups"][str(interaction.channel.id)]

        organizer_id = group_config.get("organizer_id")

        if not organizer_id:
            return

        if not new_organizer:
            user = await self.bot.fetch_user(organizer_id)
            await interaction.edit_original_response(content=f"Organisatorin: @{user.name}#{user.discriminator}")
        elif isinstance(group_config, dict):
            organizer = await self.bot.fetch_user(organizer_id)
            if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
                group_config["organizer_id"] = new_organizer.id
                await self.remove_member_from_group(interaction.channel, new_organizer, False)
                if new_organizer != organizer:
                    await self.add_member_to_group(interaction.channel, organizer, False)
                await self.save_groups()
                await self.update_permissions(interaction.channel)
                await interaction.edit_original_response(content=
                                                         f"Glückwunsch {new_organizer.mention}! Du bist jetzt die Organisatorin dieser Lerngruppe.")

    @app_commands.command(name="add-member", description="Fügt eine Benutzerin zu einer Lerngruppe hinzu.")
    @app_commands.describe(member="Die so erwähnte Benutzerin wird zur Lerngruppe hinzugefügt.",
                           channel="Der Kanal, zu dem die Benutzerin hinzugefügt werden soll.")
    async def cmd_add_member(self, interaction: Interaction, member: discord.Member,
                             channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        if not channel:
            if not self.channels.get(str(interaction.channel.id)):
                await interaction.edit_original_response(content="Wenn das Kommando außerhalb eines Lerngruppenkanals "
                                                                 "aufgerufen wird, muss der Lerngruppenkanal angefügt "
                                                                 "werden. `!lg addmember <@usermention> <#channel>`")
                return
            channel = interaction.channel
        if self.is_group_organizer(channel, interaction.user) or utils.is_mod(interaction):
            await self.add_member_to_group(channel, member)
            await self.update_permissions(channel)
        await interaction.edit_original_response(content=f"{member.mention} wurde der Lerngruppe hinzugefügt.")

    @app_commands.command(name="remove-member", description="Entfernt eine Benutzerin aus einer Lerngruppe.")
    @app_commands.describe(member="Die so erwähnte Benutzerin wird aus der Lerngruppe entfernt.",
                           channel="Der Kanal, aus dem die Benutzerin gelöscht werden soll.")
    @app_commands.checks.has_role("Mod")
    async def cmd_remove_member(self, interaction: Interaction, member: discord.Member,
                                channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await self.remove_member_from_group(channel, member)
        await self.update_permissions(channel)
        await interaction.edit_original_response(content=f"{member.mention} wurde aus der Lerngruppe entfernt.")

    @app_commands.command(name="members", description="Zählt die Mitglieder der Lerngruppe auf.")
    async def cmd_members(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        group_config = self.groups["groups"].get(str(interaction.channel.id))
        if not group_config:
            await interaction.edit_original_response(content="Das ist kein Lerngruppenkanal.")
            return
        organizer_id = group_config.get("organizer_id")

        if not organizer_id:
            await interaction.edit_original_response(
                content="Scheinbar hat die Gruppe aus irgendnem Grund keinen Organizer. Keine Ahnung... ")
            return

        organizer = await self.bot.fetch_user(organizer_id)
        users = group_config.get("users", {})
        if not users and not organizer:
            await interaction.edit_original_response(content="Keine Lerngruppenmitglieder vorhanden.")
            return

        names = []

        for user_id in users:
            user = await self.bot.fetch_user(user_id)
            names.append("@" + user.name + "#" + user.discriminator)

        await interaction.edit_original_response(
            content=f"Organisatorin: **@{organizer.name}#{organizer.discriminator}**\nMitglieder: " +
                    (f"{', '.join(names)}" if len(names) > 0 else "Keine"))

    @app_commands.command(name="id", description="Zeigt die ID für deine Lerngruppe an.")
    async def cmd_id(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
            group_config = self.groups["groups"].get(str(interaction.channel.id))
            if not group_config:
                await interaction.edit_original_response(content="Das ist kein Lerngruppenkanal.")
                return
        await interaction.edit_original_response(
            content=f"Die ID dieser Lerngruppe lautet: `{str(interaction.channel.id)}`.\n"
                    f"Beitrittsanfrage mit: `!lg join {str(interaction.channel.id)}`")

    @app_commands.command(name="join", description="Fragt bei der Organisatorin einer Lerngruppe um Aufnahme an.")
    @app_commands.describe(id_or_channel="Die ID der Lerngruppe.")
    async def cmd_join(self, interaction: Interaction, id_or_channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        if id_or_channel is None:
            id_or_channel = interaction.channel

        cid = id_or_channel.id if type(id_or_channel) is discord.TextChannel else id_or_channel

        group_config = self.groups["groups"].get(str(cid))
        if not group_config:
            await interaction.edit_original_response(content="Das ist keine gültiger Lerngruppenkanal.")
            return

        channel = await self.bot.fetch_channel(int(cid))

        await utils.confirm(
            channel=channel,
            title="Jemand möchte deiner Lerngruppe beitreten!",
            description=f"<@!{interaction.author.id}> möchte gerne der Lerngruppe **#{channel.name}** beitreten.",
            message=f"<@!{group_config['organizer_id']}>, du wirst gebraucht. Anfrage von <@!{interaction.author.id}>:",
            custom_prefix="learninggroups:join"
        )
        await utils.send_dm(interaction.author, f"Deine Anfrage wurde an **#{channel.name}** gesendet. "
                                                "Sobald die Organisatorin der Lerngruppe darüber "
                                                "entschieden hat, bekommst du Bescheid.")

    @app_commands.command(name="kick", description="Wirft @usermention aus der Gruppe.")
    @app_commands.describe(member="Mitglied, dass du aus der Gruppe werfen möchtest")
    async def cmd_kick(self, interaction: Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if self.is_group_organizer(interaction.channel, interaction.user) or utils.is_mod(interaction):
            group_config = self.groups["groups"].get(str(interaction.channel.id))
            if not group_config:
                await interaction.edit_original_response(content="Das ist keine gültiger Lerngruppenkanal.")
                return

            await self.remove_member_from_group(interaction.channel, member)
            await self.update_permissions(interaction.channel)

        await interaction.edit_original_response(content=f"{member.mention} wurde aus der Gruppe geworfen.")

    @app_commands.command(name="leave", description="Du verlässt die Lerngruppe.")
    async def cmd_leave(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        group_config = self.groups["groups"].get(str(interaction.channel.id))
        if not group_config:
            await interaction.edit_original_response(content="Das ist keine gültiger Lerngruppenkanal.")
            return

        if group_config["organizer_id"] == interaction.author.id:
            await interaction.edit_original_response(content=
                                                     "Du kannst nicht aus deiner eigenen Lerngruppe flüchten. Gib erst die Verantwortung ab.")
            return

        await self.remove_member_from_group(interaction.channel, interaction.user)
        await self.update_permissions(interaction.channel)
        await interaction.edit_original_response(content="Du hast die Gruppe verlassen.")

    async def on_group_request(self, confirmed, button, interaction: InteractionMessage):
        channel = interaction.channel
        member = interaction.author
        message = interaction.message

        if str(channel.id) == str(self.channel_request):
            request = self.groups["requested"].get(str(message.id))
            if confirmed and self.is_mod(member):
                await self.add_requested_group_channel(message, direct=False)

            elif not confirmed and (self.is_request_organizer(request, member) or self.is_mod(member)):
                if self.is_mod(member):
                    user = await self.bot.fetch_user(request["organizer_id"])
                    if user:
                        await utils.send_dm(user,
                                            f"Deine Lerngruppenanfrage für #{self.full_channel_name(request)} wurde abgelehnt.")
                await self.remove_group_request(message)

                await message.delete()

    async def on_join_request(self, confirmed, button, interaction: InteractionMessage):
        channel = interaction.channel
        member = interaction.author
        message = interaction.message
        group_config = self.groups["groups"].get(str(channel.id))

        if not group_config:
            return

        if self.is_group_organizer(channel, member) or self.is_mod(member):
            if confirmed:
                if message.mentions and len(message.mentions) == 2:
                    await self.add_member_to_group(channel, message.mentions[1])
                    await self.update_permissions(channel)

                else:
                    await channel.send(f"Leider ist ein Fehler aufgetreten.")
            else:
                if message.mentions and len(message.mentions) == 1:
                    await utils.send_dm(message.mentions[0], f"Deine Anfrage für die Lerngruppe **#{channel.name}**"
                                                             "wurde abgelehnt.")
            await message.delete()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LearningGroups(bot))
