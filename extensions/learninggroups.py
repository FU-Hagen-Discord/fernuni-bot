import copy
import json
import os
import re
import time
from enum import Enum

import discord
from discord import app_commands, Interaction
from discord.ext import commands

import utils
from models import Module
from views.learninggroup_view import GroupRequestView, JoinRequestView, ConfirmView

"""
  Umgebungsvariablen:
  DISCORD_LEARNINGGROUPS_OPEN - Kategorie-ID der offenen Lerngruppen
  DISCORD_LEARNINGGROUPS_CLOSE - Kategorie-ID der geschlossenen Lerngruppen
  DISCORD_LEARNINGGROUPS_PRIVATE - Kategorie-ID der privaten Lerngruppen
  DISCORD_LEARNINGGROUPS_ARCHIVE - Kategorie-ID der archivierten Lerngruppen
  DISCORD_LEARNINGGROUPS_REQUEST - ID des Kanals, in dem Anfragen, die über den Bot gestellt wurden, eingetragen werden
  DISCORD_LEARNINGGROUPS_INFO - ID des Kanals, in dem die Lerngruppen-Informationen gepostet/aktualisert werden
  DISCORD_LEARNINGGROUPS_FILE - Name der Datei mit Verwaltungsdaten der Lerngruppen (minimaler Inhalt: {"requested": {},"groups": {}})
  DISCORD_LEARNINGGROUPS_COURSE_FILE - Name der Datei, welche Überschriften für die Lerngruppen-Informationen enthält,
                                       die nicht aus der Modul-Tabelle kommen (minimaler Inhalt: {})
  DISCORD_SUPPORT_CHANNEL - ID des Kanals, in dem fehlende Überschriften gemeldet werden
  DISCORD_MOD_ROLE - ID der Moderations-Rolle, die erweiterte Lerngruppen-Aktionen ausführen darf
"""

LG_OPEN_SYMBOL = f'🌲'
LG_CLOSE_SYMBOL = f'🛑'
LG_PRIVATE_SYMBOL = f'🚪'
LG_LISTED_SYMBOL = f'📖'

NO_PERMISSION = "Du hast nicht die notwendigen Berechtigungen, um diese Aktion auszuführen."
NO_LEARNING_GROUP = "Das ist kein Lerngruppenkanal."


class LearningGroupState(Enum):
    offen = "OPEN"
    geschlossen = "CLOSED"
    privat = "PRIVATE"


class GroupState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRIVATE = "PRIVATE"
    ARCHIVED = "ARCHIVED"
    REMOVED = "REMOVED"


class LearningGroups(commands.Cog):
    lg = app_commands.Group(name="lg", description="Lerngruppenverwaltung.", guild_only=True)
    lg_admin = app_commands.Group(name="lg-admin", description="Administration der Lerngruppen.", guild_only=True,
                                  default_permissions=discord.Permissions(manage_channels=True))

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
        self.groups = {}  # organizer and learninggroup-member ids
        self.channels = {}  # complete channel configs
        self.header = {}  # headlines for status message
        self.load_groups()
        self.load_header()

    @commands.Cog.listener(name="on_ready")
    async def on_ready(self):
        await self.update_channels()

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"Bitte warte noch {int(error.retry_after) + 1} Sekunden, bevor du das erneut versuchst."
        elif isinstance(error, app_commands.CheckFailure):
            message = NO_PERMISSION
        else:
            return

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    # Data handling

    def load_header(self):
        with open(self.header_file, mode='r') as file:
            self.header = json.load(file)

    def save_header(self):
        with open(self.header_file, mode='w') as file:
            json.dump(self.header, file)

    def load_groups(self):
        with open(self.group_file, mode='r') as group_file:
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
        groups = copy.deepcopy(self.groups)

        for _, group in groups['requested'].items():
            group["state"] = group["state"].name

        with open(self.group_file, mode='w') as group_file:
            json.dump(groups, group_file)

    # Helper methods

    @staticmethod
    def normalize_name(name: str) -> str:
        return re.sub(r"[^a-zäöüß0-9-]", "", name.lower().replace(" ", "-"))

    @staticmethod
    def normalize_semester(semester: str) -> str:
        semester = re.sub(r"[^wiseo0-9]", "", semester.lower())
        if len(semester) == 8:
            semester = f"{semester[0:4]}{semester[-2:]}"
        return semester

    @staticmethod
    def validate_channel_config(channel_config) -> str | None:
        if not channel_config['name']:
            return "Fehler! Der Name der Lerngruppe darf nur aus Buchstaben, Zahlen und Bindestrichen bestehen."
        if not re.match(r"^(sose|wise)[0-9]{2}$", channel_config['semester']):
            return ("Fehler! Das Semester muss mit **sose** oder **wise** angegeben werden, gefolgt von der "
                    "**zweistelligen Jahreszahl** (z. B. sose22).")
        return None

    async def get_channel(self, channel_id):
        return self.bot.get_channel(int(channel_id)) or await self.bot.fetch_channel(int(channel_id))

    def get_group_config(self, channel):
        return self.groups["groups"].get(str(channel.id))

    def is_group_channel(self, channel) -> bool:
        return channel is not None and str(channel.id) in self.channels and self.get_group_config(channel) is not None

    def is_group_organizer(self, channel, member) -> bool:
        group_config = self.get_group_config(channel)
        return group_config is not None and group_config.get("organizer_id") == member.id

    def is_group_member(self, channel, member) -> bool:
        group_config = self.get_group_config(channel)
        return group_config is not None and str(member.id) in group_config.get("users", {})

    def is_organizer_or_mod(self, channel, member) -> bool:
        return self.is_group_organizer(channel, member) or utils.is_mod(member)

    def rename_cooldown(self, channel) -> int:
        """ Returns the number of seconds until the channel can be renamed again. """

        last_rename = self.get_group_config(channel).get("last_rename")
        if last_rename is None:
            return 0
        return max(0, last_rename + self.rename_ratelimit - int(time.time()))

    @staticmethod
    def rename_cooldown_message(seconds: int) -> str:
        return (f"Discord schränkt die Anzahl der Aufrufe für manche Funktionen ein, daher kannst du diese Aktion "
                f"erst wieder in {seconds} Sekunden ausführen.")

    async def ensure_group_channel(self, interaction: Interaction, channel=None) -> bool:
        """ Checks, whether the given channel (or the channel of the interaction) is a learning group channel and
        responds with an error message if not. """

        if self.is_group_channel(channel or interaction.channel):
            return True

        await interaction.edit_original_response(content=NO_LEARNING_GROUP)
        return False

    def course_header(self, course: str) -> str | None:
        if header := self.header.get(course):
            return header
        if module := Module.get_or_none(Module.number == int(course)):
            return f"{module.number} - {module.title}"
        return None

    async def category_of_channel(self, state: GroupState):
        return await self.get_channel(self.categories[state])

    def full_channel_name(self, channel_config):
        return (f"{self.symbols[channel_config['state']]}"
                f"{channel_config['course']}-{channel_config['name']}-{channel_config['semester']}"
                f"{LG_LISTED_SYMBOL if channel_config['is_listed'] else ''}")

    def channel_to_channel_config(self, channel):
        cid = str(channel.id)
        is_listed = channel.name[-1] == LG_LISTED_SYMBOL
        result = re.match(r"([0-9]+)-(.*)-([a-z0-9]+)$", channel.name[1:] if not is_listed else channel.name[1:-1])
        if not result:
            return None

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
                if channel_config := self.channel_to_channel_config(channel):
                    self.channels[str(channel.id)] = channel_config

    async def update_statusmessage(self):
        channel = await self.get_channel(self.channel_info)

        for info_message_id in self.groups.get("messageids"):
            try:
                message = await channel.fetch_message(info_message_id)
                await message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        info_message_ids = []

        msg = f"**Lerngruppen**\n\n"
        course_msg = ""
        sorted_channels = sorted(self.channels.values(), key=lambda channel: f"{channel['course']}-{channel['name']}")
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
                header = self.course_header(lg_channel['course'])
                if header:
                    course_msg += f"**{header}**\n"
                else:
                    course_msg += f"**{lg_channel['course']} - -------------------------------------**\n"
                    no_headers.append(lg_channel['course'])
                courseheader = lg_channel['course']

            course_msg += f"    <#{lg_channel['channel_id']}>"

            if lg_channel['is_listed'] and lg_channel['state'] == GroupState.PRIVATE:
                group_config = self.groups["groups"].get(lg_channel['channel_id'])
                if group_config and (organizer_id := group_config.get('organizer_id')):
                    user = self.bot.get_user(organizer_id) or await self.bot.fetch_user(organizer_id)
                    course_msg += f" **@{user.name}**"
                course_msg += f"\n       **↳** `/lg join id:{lg_channel['channel_id']}`"
            course_msg += "\n"

        msg += course_msg
        message = await channel.send(msg)
        if len(no_headers) > 0:
            support_channel = await self.get_channel(self.support_channel)
            if support_channel:
                await support_channel.send(
                    f"In der Lerngruppenübersicht fehlen noch Überschriften für die folgenden Module: "
                    f"**{', '.join(no_headers)}**. Diese können mit `/lg-admin header` ergänzt werden.")
        info_message_ids.append(message.id)
        self.groups["messageids"] = info_message_ids
        await self.save_groups()

    async def archive(self, channel):
        category = await self.get_channel(self.categories[GroupState.ARCHIVED])
        await self.move_channel(channel, category)
        await channel.edit(name=f"archiv-{channel.name[1:]}")
        await self.update_permissions(channel)
        await self.remove_group(channel)
        await self.update_statusmessage()

    async def set_channel_state(self, channel, state: GroupState):
        channel_config = self.channels[str(channel.id)]
        channel_config["state"] = state
        await self.alter_channel(channel, channel_config)

    async def set_channel_listing(self, channel, is_listed: bool):
        channel_config = self.channels[str(channel.id)]
        channel_config["is_listed"] = is_listed
        await self.alter_channel(channel, channel_config)

    async def alter_channel(self, channel, channel_config):
        self.groups["groups"][str(channel.id)]["last_rename"] = int(time.time())
        await channel.edit(name=self.full_channel_name(channel_config))
        category = await self.category_of_channel(channel_config["state"])
        await self.move_channel(channel, category,
                                sync=channel_config["state"] in [GroupState.OPEN, GroupState.CLOSED])
        await self.save_groups()
        await self.update_statusmessage()

    async def set_channel_name(self, channel, name):
        channel_config = self.channels[str(channel.id)]
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

    async def create_group_channel(self, channel_config):
        category = await self.category_of_channel(channel_config["state"])
        channel = await category.create_text_channel(self.full_channel_name(channel_config))
        await self.move_channel(channel, category, False)

        await channel.send(f":wave: <@{channel_config['organizer_id']}>, hier ist deine neue Lerngruppe.\n"
                           "Es gibt offene und private Lerngruppen. Eine offene Lerngruppe ist für jeden sichtbar "
                           "und jeder kann darin schreiben. Eine private Lerngruppe ist unsichtbar und auf eine "
                           "Gruppe an Kommilitoninnen beschränkt."
                           "```"
                           "Funktionen für Lerngruppenorganisatorinnen:\n"
                           "/lg add-member: Fügt ein Mitglied zur Lerngruppe hinzu.\n"
                           "/lg remove-member: Entfernt ein Mitglied aus der Lerngruppe.\n"
                           "/lg organizer: Übergibt die Organisation der Lerngruppe an eine andere Benutzerin.\n"
                           "/lg status: Stellt die Lerngruppe auf offen, geschlossen oder privat.\n"
                           "/lg show: Zeigt eine private Lerngruppe in der Lerngruppenliste an.\n"
                           "/lg hide: Entfernt eine private Lerngruppe aus der Lerngruppenliste.\n"
                           "\nKommandos für alle:\n"
                           "/lg members: Zeigt die Organisatorin und die Mitglieder der Lerngruppe an.\n"
                           "/lg leave: Du verlässt die Lerngruppe.\n"
                           "/lg join: Anfrage, um der Lerngruppe beizutreten.\n"
                           "\nMit dem nachfolgenden Kommando kann eine Kommilitonin darum "
                           "bitten, in die Lerngruppe aufgenommen zu werden, wenn die Gruppe privat ist.\n"
                           f"/lg join id:{channel.id}"
                           "\n(Manche Kommandos werden von Discord eingeschränkt und können nur einmal alle 5 Minuten "
                           "ausgeführt werden.)"
                           "```"
                           )
        self.groups["groups"][str(channel.id)] = {
            "organizer_id": channel_config["organizer_id"],
            "last_rename": int(time.time())
        }

        await self.save_groups()
        await self.update_statusmessage()
        if channel_config["state"] is GroupState.PRIVATE:
            await self.update_permissions(channel, GroupState.PRIVATE)

        return channel

    async def remove_group_request(self, message):
        del self.groups["requested"][str(message.id)]
        await self.save_groups()

    async def remove_group(self, channel):
        del self.groups["groups"][str(channel.id)]
        await self.save_groups()

    async def add_member_to_group(self, channel: discord.TextChannel, member: discord.Member, send_message=True):
        group_config = self.get_group_config(channel)
        users = group_config.setdefault("users", {})
        mid = str(member.id)
        if not users.get(mid):
            users[mid] = True
            if send_message:
                await utils.send_dm(member, f"Du wurdest in die Lerngruppe <#{channel.id}> aufgenommen. "
                                            "Viel Spass beim gemeinsamen Lernen!\n"
                                            "Dieser Link führt dich direkt zum Lerngruppenkanal. "
                                            "Diese Nachricht kannst du in unserer Unterhaltung mit Rechtsklick "
                                            "anpinnen, wenn du möchtest.")

        await self.save_groups()

    async def remove_member_from_group(self, channel: discord.TextChannel, member: discord.Member,
                                       send_message=True):
        group_config = self.get_group_config(channel)
        users = group_config.get("users")
        if not users:
            return
        if users.pop(str(member.id), None) and send_message:
            await utils.send_dm(member, f"Du wurdest aus der Lerngruppe {channel.name} entfernt.")

        await self.save_groups()

    async def update_permissions(self, channel, state: GroupState = None):
        state = state or self.channels.get(str(channel.id), {}).get("state")
        if state == GroupState.PRIVATE:
            await channel.edit(overwrites=self.overwrites(channel))
        else:
            await channel.edit(sync_permissions=True)

    def overwrites(self, channel):
        group_config = self.get_group_config(channel)
        guild = channel.guild
        mods = guild.get_role(int(os.getenv("DISCORD_MOD_ROLE")))

        overwrites = {
            mods: discord.PermissionOverwrite(read_messages=True),
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        if not group_config or not group_config.get("organizer_id"):
            return overwrites

        user_ids = [group_config["organizer_id"]] + list(group_config.get("users", {}).keys())
        for user_id in user_ids:
            overwrites[discord.Object(id=int(user_id), type=discord.Member)] = discord.PermissionOverwrite(
                read_messages=True)

        return overwrites

    # Commands for everyone

    @lg.command(name="request", description="Stellt eine Anfrage für einen neuen Lerngruppenkanal.")
    @app_commands.describe(
        module="Nummer des Moduls, wie von der FernUni angegeben (ohne führende Nullen).",
        name="Ein frei wählbarer Name für die Lerngruppe.",
        semester="Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der "
                 "zweistelligen Jahreszahl (z. B. sose22).",
        state="Gibt an, ob die Lerngruppe für weitere Lernwillige geöffnet ist (offen) oder nicht (geschlossen) oder "
              "ob es sich um eine private Lerngruppe handelt (privat).")
    async def cmd_request(self, interaction: Interaction, module: app_commands.Range[int, 1], name: str,
                          semester: str, state: LearningGroupState):
        await interaction.response.defer(ephemeral=True)
        channel_config = {"organizer_id": interaction.user.id, "course": str(module),
                          "name": self.normalize_name(name), "semester": self.normalize_semester(semester),
                          "state": GroupState(state.value), "is_listed": False}

        if error := self.validate_channel_config(channel_config):
            await interaction.edit_original_response(content=error)
            return

        channel = await self.get_channel(self.channel_request)
        embed = discord.Embed(title="Lerngruppenanfrage",
                              description=f"{interaction.user.mention} möchte gerne die Lerngruppe "
                                          f"**#{self.full_channel_name(channel_config)}** eröffnen.",
                              color=19607)
        message = await channel.send(embed=embed, view=GroupRequestView(self))
        self.groups["requested"][str(message.id)] = channel_config
        await self.save_groups()
        await interaction.edit_original_response(content="Deine Lerngruppenanfrage wurde an die Moderatorinnen zur "
                                                         "Genehmigung weitergeleitet. Du erhältst eine Nachricht, "
                                                         "wenn über deine Anfrage entschieden wurde.")

    @lg.command(name="show", description="Zeigt eine private Lerngruppe in der Lerngruppenliste an.")
    async def cmd_show(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.change_listing(interaction, True)

    @lg.command(name="hide", description="Entfernt eine private Lerngruppe aus der Lerngruppenliste.")
    async def cmd_hide(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.change_listing(interaction, False)

    async def change_listing(self, interaction: Interaction, is_listed: bool):
        if not await self.ensure_group_channel(interaction):
            return
        if not self.is_organizer_or_mod(interaction.channel, interaction.user):
            await interaction.edit_original_response(content=NO_PERMISSION)
            return

        channel_config = self.channels[str(interaction.channel.id)]
        if channel_config["state"] == GroupState.OPEN:
            await interaction.edit_original_response(
                content="Offene Lerngruppen werden immer in der Lerngruppenliste angezeigt. Mit `/lg status` kannst "
                        "du die Lerngruppe auf privat stellen.")
            return
        if channel_config["state"] == GroupState.CLOSED:
            await interaction.edit_original_response(
                content="Nur private Lerngruppen können in der Lerngruppenliste angezeigt oder daraus entfernt "
                        "werden. Mit `/lg status` kannst du den Status der Lerngruppe ändern.")
            return
        if channel_config["is_listed"] == is_listed:
            await interaction.edit_original_response(
                content=f"Die Lerngruppe wird bereits {'' if is_listed else 'nicht '}in der Lerngruppenliste "
                        f"angezeigt.")
            return
        if seconds := self.rename_cooldown(interaction.channel):
            await interaction.edit_original_response(content=self.rename_cooldown_message(seconds))
            return

        await self.set_channel_listing(interaction.channel, is_listed)
        await interaction.edit_original_response(
            content=f"Die Lerngruppe wird nun {'' if is_listed else 'nicht mehr '}in der Lerngruppenliste angezeigt.")

    @lg.command(name="status", description="Stellt die Lerngruppe auf offen, geschlossen oder privat.")
    @app_commands.describe(
        state="offen: für alle sichtbar und offen für neue Mitglieder. geschlossen: für alle sichtbar, aber keine "
              "neuen Mitglieder. privat: nur für Mitglieder sichtbar.")
    async def cmd_status(self, interaction: Interaction, state: LearningGroupState):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_group_channel(interaction):
            return
        if not self.is_organizer_or_mod(interaction.channel, interaction.user):
            await interaction.edit_original_response(content=NO_PERMISSION)
            return

        group_state = GroupState(state.value)
        if self.channels[str(interaction.channel.id)]["state"] == group_state:
            await interaction.edit_original_response(content=f"Die Lerngruppe ist bereits {state.name}.")
            return
        if seconds := self.rename_cooldown(interaction.channel):
            await interaction.edit_original_response(content=self.rename_cooldown_message(seconds))
            return

        await self.set_channel_state(interaction.channel, group_state)
        if group_state == GroupState.PRIVATE:
            await self.update_permissions(interaction.channel, group_state)
        await interaction.edit_original_response(content=f"Die Lerngruppe ist jetzt {state.name}.")

    @lg.command(name="organizer", description="Übergibt die Organisation der Lerngruppe an eine andere Benutzerin.")
    @app_commands.describe(new_organizer="Die neue Organisatorin der Lerngruppe.")
    async def cmd_organizer(self, interaction: Interaction, new_organizer: discord.Member):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        if not await self.ensure_group_channel(interaction):
            return
        if not self.is_organizer_or_mod(channel, interaction.user):
            await interaction.edit_original_response(content=NO_PERMISSION)
            return
        if new_organizer.bot:
            await interaction.edit_original_response(content="Ein Bot kann keine Lerngruppe organisieren.")
            return
        if self.is_group_organizer(channel, new_organizer):
            await interaction.edit_original_response(
                content=f"{new_organizer.mention} ist bereits die Organisatorin dieser Lerngruppe.")
            return

        group_config = self.get_group_config(channel)
        old_organizer_id = group_config.get("organizer_id")
        group_config["organizer_id"] = new_organizer.id
        await self.remove_member_from_group(channel, new_organizer, False)
        if old_organizer_id:
            group_config.setdefault("users", {})[str(old_organizer_id)] = True
        await self.save_groups()
        await self.update_permissions(channel)
        await channel.send(f"Glückwunsch {new_organizer.mention}! Du bist jetzt die Organisatorin dieser Lerngruppe.")
        await interaction.edit_original_response(content="Die Organisation der Lerngruppe wurde übergeben.")

    @lg.command(name="add-member", description="Fügt eine Benutzerin zu einer Lerngruppe hinzu.")
    @app_commands.describe(member="Die Benutzerin, die zur Lerngruppe hinzugefügt werden soll.",
                           channel="Der Lerngruppenkanal, falls das Kommando außerhalb der Lerngruppe genutzt wird.")
    async def cmd_add_member(self, interaction: Interaction, member: discord.Member,
                             channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        channel = channel or interaction.channel
        if not await self.ensure_group_channel(interaction, channel):
            return
        if not self.is_organizer_or_mod(channel, interaction.user):
            await interaction.edit_original_response(content=NO_PERMISSION)
            return
        if member.bot:
            await interaction.edit_original_response(content="Bots können keiner Lerngruppe beitreten.")
            return
        if self.is_group_organizer(channel, member) or self.is_group_member(channel, member):
            await interaction.edit_original_response(
                content=f"{member.mention} ist bereits Mitglied der Lerngruppe {channel.mention}.")
            return

        await self.add_member_to_group(channel, member)
        await self.update_permissions(channel)
        await interaction.edit_original_response(
            content=f"{member.mention} wurde der Lerngruppe {channel.mention} hinzugefügt.")

    @lg.command(name="remove-member", description="Entfernt eine Benutzerin aus einer Lerngruppe.")
    @app_commands.describe(member="Die Benutzerin, die aus der Lerngruppe entfernt werden soll.",
                           channel="Der Lerngruppenkanal, falls das Kommando außerhalb der Lerngruppe genutzt wird.")
    async def cmd_remove_member(self, interaction: Interaction, member: discord.Member,
                                channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        channel = channel or interaction.channel
        if not await self.ensure_group_channel(interaction, channel):
            return
        if not self.is_organizer_or_mod(channel, interaction.user):
            await interaction.edit_original_response(content=NO_PERMISSION)
            return
        if self.is_group_organizer(channel, member):
            await interaction.edit_original_response(
                content="Die Organisatorin kann nicht aus der Lerngruppe entfernt werden. Übergib die Organisation "
                        "vorher mit `/lg organizer` an eine andere Benutzerin.")
            return
        if not self.is_group_member(channel, member):
            await interaction.edit_original_response(
                content=f"{member.mention} ist kein Mitglied der Lerngruppe {channel.mention}.")
            return

        await self.remove_member_from_group(channel, member)
        await self.update_permissions(channel)
        await interaction.edit_original_response(
            content=f"{member.mention} wurde aus der Lerngruppe {channel.mention} entfernt.")

    @lg.command(name="members", description="Zeigt die Organisatorin und die Mitglieder der Lerngruppe an.")
    async def cmd_members(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_group_channel(interaction):
            return

        group_config = self.get_group_config(interaction.channel)
        organizer_id = group_config.get("organizer_id")
        organizer = f"<@{organizer_id}>" if organizer_id else "Keine"
        members = [f"<@{user_id}>" for user_id in group_config.get("users", {})]

        await interaction.edit_original_response(
            content=f"Organisatorin: **{organizer}**\nMitglieder: {', '.join(members) if members else 'Keine'}",
            allowed_mentions=discord.AllowedMentions.none())

    @lg.command(name="join", description="Fragt bei der Organisatorin einer Lerngruppe um Aufnahme an.")
    @app_commands.describe(id="Die ID der Lerngruppe. Ohne Angabe wird die Lerngruppe genutzt, in der du dich befindest.")
    @app_commands.checks.cooldown(3, 600, key=lambda interaction: interaction.user.id)
    async def cmd_join(self, interaction: Interaction, id: str = None):
        await interaction.response.defer(ephemeral=True)
        cid = re.sub(r"[^0-9]", "", id) if id else str(interaction.channel.id)
        group_config = self.groups["groups"].get(cid)
        if not cid or cid not in self.channels or not group_config:
            await interaction.edit_original_response(content="Das ist keine gültige Lerngruppe.")
            return

        channel = await self.get_channel(cid)
        if self.is_group_organizer(channel, interaction.user):
            await interaction.edit_original_response(content="Du bist die Organisatorin dieser Lerngruppe.")
            return
        if self.is_group_member(channel, interaction.user):
            await interaction.edit_original_response(content="Du bist bereits Mitglied dieser Lerngruppe.")
            return

        embed = discord.Embed(title="Jemand möchte deiner Lerngruppe beitreten!",
                              description=f"{interaction.user.mention} möchte gerne der Lerngruppe "
                                          f"**#{channel.name}** beitreten.",
                              color=19607)
        embed.add_field(name="Anfrage von", value=interaction.user.mention)
        await channel.send(f"<@{group_config.get('organizer_id')}>, du wirst gebraucht. "
                           f"Anfrage von {interaction.user.mention}:", embed=embed, view=JoinRequestView(self))
        await interaction.edit_original_response(content=f"Deine Anfrage wurde an **#{channel.name}** gesendet. "
                                                         "Sobald die Organisatorin der Lerngruppe darüber "
                                                         "entschieden hat, bekommst du Bescheid.")

    @lg.command(name="leave", description="Du verlässt die Lerngruppe.")
    async def cmd_leave(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_group_channel(interaction):
            return
        if self.is_group_organizer(interaction.channel, interaction.user):
            await interaction.edit_original_response(
                content="Du kannst nicht aus deiner eigenen Lerngruppe flüchten. Gib erst die Verantwortung mit "
                        "`/lg organizer` ab.")
            return
        if not self.is_group_member(interaction.channel, interaction.user):
            await interaction.edit_original_response(content="Du bist kein Mitglied dieser Lerngruppe.")
            return

        await self.remove_member_from_group(interaction.channel, interaction.user, False)
        await self.update_permissions(interaction.channel)
        await interaction.edit_original_response(content="Du hast die Lerngruppe verlassen.")

    # Admin commands

    @lg_admin.command(name="update", description="Aktualisiert die Lerngruppenliste.")
    @utils.mod_only()
    async def cmd_update(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.update_channels()
        await self.update_statusmessage()
        await interaction.edit_original_response(content="Die Lerngruppenliste wurde aktualisiert.")

    @lg_admin.command(name="header",
                      description="Fügt eine Überschrift für ein Modul in der Lerngruppenliste hinzu oder ändert sie.")
    @app_commands.describe(
        module="Nummer des Moduls, wie von der FernUni angegeben (ohne führende Nullen).",
        name="Ein frei wählbarer Text (darf Leerzeichen enthalten).")
    @utils.mod_only()
    async def cmd_header(self, interaction: Interaction, module: app_commands.Range[int, 1], name: str):
        await interaction.response.defer(ephemeral=True)
        self.header[str(module)] = f"{module} - {name}"
        self.save_header()
        await self.update_statusmessage()
        await interaction.edit_original_response(content=f"Überschrift **{module} - {name}** gespeichert.")

    @lg_admin.command(name="add", description="Legt direkt einen neuen Lerngruppenkanal an.")
    @app_commands.describe(
        module="Nummer des Moduls, wie von der FernUni angegeben (ohne führende Nullen).",
        name="Ein frei wählbarer Name für die Lerngruppe.",
        semester="Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der "
                 "zweistelligen Jahreszahl (z. B. sose22).",
        state="Gibt an, ob die Lerngruppe offen, geschlossen oder privat ist.",
        organizer="Die Organisatorin der Lerngruppe.")
    @utils.mod_only()
    async def cmd_add(self, interaction: Interaction, module: app_commands.Range[int, 1], name: str, semester: str,
                      state: LearningGroupState, organizer: discord.Member):
        await interaction.response.defer(ephemeral=True)
        channel_config = {"organizer_id": organizer.id, "course": str(module), "name": self.normalize_name(name),
                          "semester": self.normalize_semester(semester), "state": GroupState(state.value),
                          "is_listed": False}

        if error := self.validate_channel_config(channel_config):
            await interaction.edit_original_response(content=error)
            return

        channel = await self.create_group_channel(channel_config)
        await interaction.edit_original_response(content=f"Die Lerngruppe {channel.mention} wurde angelegt.")

    @lg_admin.command(name="rename", description="Ändert den Namen des Lerngruppenkanals, in dem du dich befindest.")
    @app_commands.describe(name="Der neue Name der Lerngruppe.")
    @utils.mod_only()
    async def cmd_rename(self, interaction: Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_group_channel(interaction):
            return

        name = self.normalize_name(name)
        if not name:
            await interaction.edit_original_response(
                content="Der Name der Lerngruppe darf nur aus Buchstaben, Zahlen und Bindestrichen bestehen.")
            return
        if seconds := self.rename_cooldown(interaction.channel):
            await interaction.edit_original_response(content=self.rename_cooldown_message(seconds))
            return

        await self.set_channel_name(interaction.channel, name)
        await interaction.edit_original_response(content=f"Die Lerngruppe heißt jetzt {interaction.channel.mention}.")

    @lg_admin.command(name="archive", description="Verschiebt den Lerngruppenkanal, in dem du dich befindest, ins Archiv.")
    @utils.mod_only()
    async def cmd_archive(self, interaction: Interaction):
        channel = interaction.channel
        if not self.is_group_channel(channel):
            await interaction.response.send_message(NO_LEARNING_GROUP, ephemeral=True)
            return

        view = ConfirmView(interaction.user.id, "Archivieren")
        await interaction.response.send_message(f"Soll die Lerngruppe {channel.mention} wirklich archiviert werden?",
                                                view=view, ephemeral=True)
        await view.wait()
        if not view.confirmed:
            await interaction.edit_original_response(content="Archivierung abgebrochen.", view=None)
            return

        await interaction.edit_original_response(content="Die Lerngruppe wird archiviert...", view=None)
        await self.archive(channel)
        await interaction.edit_original_response(content=f"Die Lerngruppe {channel.mention} wurde archiviert.")

    # Button handlers

    async def on_group_request(self, interaction: Interaction, confirmed: bool):
        message = interaction.message
        member = interaction.user
        request = self.groups["requested"].get(str(message.id))

        if not request:
            await interaction.response.send_message("Diese Anfrage existiert nicht mehr.", ephemeral=True)
            return
        if not (utils.is_mod(member) or (not confirmed and request["organizer_id"] == member.id)):
            await interaction.response.send_message(NO_PERMISSION, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        if confirmed:
            channel = await self.create_group_channel(request)
            await interaction.followup.send(f"Die Lerngruppe {channel.mention} wurde angelegt.", ephemeral=True)
        else:
            if request["organizer_id"] != member.id:
                user = self.bot.get_user(request["organizer_id"]) or await self.bot.fetch_user(request["organizer_id"])
                await utils.send_dm(user, f"Deine Lerngruppenanfrage für #{self.full_channel_name(request)} "
                                          f"wurde abgelehnt.")
            await interaction.followup.send("Die Anfrage wurde abgelehnt.", ephemeral=True)

        await self.remove_group_request(message)
        await message.delete()

    async def on_join_request(self, interaction: Interaction, confirmed: bool):
        channel = interaction.channel
        message = interaction.message

        if not self.is_group_channel(channel):
            await interaction.response.send_message(NO_LEARNING_GROUP, ephemeral=True)
            return
        if not self.is_organizer_or_mod(channel, interaction.user):
            await interaction.response.send_message(
                "Nur die Organisatorin der Lerngruppe kann über Beitrittsanfragen entscheiden.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        requester_id = int(re.sub(r"[^0-9]", "", message.embeds[0].fields[0].value))
        requester = channel.guild.get_member(requester_id)

        if not requester:
            await interaction.followup.send("Die anfragende Benutzerin ist nicht mehr auf dem Server.",
                                            ephemeral=True)
        elif confirmed:
            await self.add_member_to_group(channel, requester)
            await self.update_permissions(channel)
            await interaction.followup.send(f"{requester.mention} wurde in die Lerngruppe aufgenommen.",
                                            ephemeral=True)
        else:
            await utils.send_dm(requester, f"Deine Anfrage für die Lerngruppe **#{channel.name}** wurde abgelehnt.")
            await interaction.followup.send(f"Die Anfrage von {requester.mention} wurde abgelehnt.", ephemeral=True)

        await message.delete()


async def setup(bot: commands.Bot) -> None:
    learning_groups = LearningGroups(bot)
    await bot.add_cog(learning_groups)
    bot.add_view(GroupRequestView(learning_groups))
    bot.add_view(JoinRequestView(learning_groups))
