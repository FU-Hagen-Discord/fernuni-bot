import copy
import json
import os
import re
import time
from enum import Enum
from typing import Union

import disnake
from disnake import InteractionMessage
from disnake.ext import commands
from disnake.ui import Button

import utils
from cogs.help import help, handle_error, help_category

"""
  Environment Variablen:
  DISCORD_LEARNINGGROUPS_OPEN - ID der Kategorie für offene Lerngruppen
  DISCORD_LEARNINGGROUPS_CLOSE - ID der Kategorie für private Lerngruppen
  DISCORD_LEARNINGGROUPS_ARCHIVE - ID der Kategorie für archivierte Lerngruppen
  DISCORD_LEARNINGGROUPS_REQUEST - ID des Channels in welchem Requests vom Bot eingestellt werden
  DISCORD_LEARNINGGROUPS_INFO - ID des Channels in welchem die Lerngruppen-Informationen gepostet/aktualisert werden
  DISCORD_LEARNINGGROUPS_FILE - Name der Datei mit Verwaltungsdaten der Lerngruppen (minimaler Inhalt: {"requested": {},"groups": {}})
  DISCORD_LEARNINGGROUPS_COURSE_FILE - Name der Datei welche die Kursnamen für die Lerngruppen-Informationen enthält (minimalter Inhalt: {})
  DISCORD_MOD_ROLE - ID der Moderator Rolle von der erweiterte Lerngruppen-Actionen ausgeführt werden dürfen
"""

LG_OPEN_SYMBOL = f'🌲'
LG_CLOSE_SYMBOL = f'🛑'
LG_PRIVATE_SYMBOL = f'🚪'
LG_LISTED_SYMBOL = f'📖'


class GroupState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRIVATE = "PRIVATE"
    ARCHIVED = "ARCHIVED"
    REMOVED = "REMOVED"


@help_category("learninggroups", "Lerngruppen",
               "Mit dem Lerngruppen-Feature kannst du Lerngruppen-Kanäle beantragen und verwalten.",
               "Hier kannst du Lerngruppen-Kanäle anlegen, beantragen und verwalten.")
class LearningGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ratelimit 2 in 10 minutes (305 * 2 = 610 = 10 minutes and 10 seconds)
        self.rename_ratelimit = 305
        self.msg_max_len = 2000

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
        self.groups = {}  # owner and learninggroup-member ids
        self.channels = {}  # complete channel configs
        self.header = {}  # headlines for statusmessage
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

    def arg_state_to_group_state(self, state: str):
        if state in ["offen", "open", "o"]:
            return GroupState.OPEN
        if state in ["geschlossen", "closed", "close"]:
            return GroupState.CLOSED
        if state in ["private", "privat"]:
            return GroupState.PRIVATE
        return None

    def is_request_owner(self, request, member):
        return request["owner_id"] == member.id

    def is_group_owner(self, channel, member):
        channel_config = self.groups["groups"].get(str(channel.id))
        if channel_config:
            return channel_config["owner_id"] == member.id
        return False

    def is_mod(self, member):
        roles = member.roles
        for role in roles:
            if role.id == int(self.mod_role):
                return True

        return False

    def is_group_request_message(self, message):
        return len(message.embeds) > 0 and message.embeds[0].title == "Lerngruppenanfrage!"

    async def is_channel_config_valid(self, ctx, channel_config, command=None):
        if channel_config['state'] is None:
            if command:
                await ctx.channel.send(
                    f"Fehler! Bitte gib an ob die Gruppe **offen** (**open**) **geschlossen** (**closed**) oder **privat** (**private**) ist. Gib `!help {command}` für Details ein.")
            return False
        if not re.match(r"^[0-9]+$", channel_config['course']):
            if command:
                await ctx.channel.send(
                    f"Fehler! Die Kursnummer muss numerisch sein. Gib `!help {command}` für Details ein.")
            return False
        if not re.match(r"^(sose|wise)[0-9]{2}$", channel_config['semester']):
            if command:
                await ctx.channel.send(
                    f"Fehler! Das Semester muss mit **sose** oder **wise** angegeben werden gefolgt von der **zweistelligen Jahreszahl**. Gib `!help {command}` für Details ein.")
            return False
        return True

    async def check_rename_rate_limit(self, channel_config):
        if channel_config.get("last_rename") is None:
            return False
        now = int(time.time())
        seconds = channel_config["last_rename"] + self.rename_ratelimit - now
        if seconds > 0:
            channel = await self.bot.fetch_channel(int(channel_config["channel_id"]))
            await channel.send(f"Discord limitiert die Aufrufe für manche Funktionen, daher kannst du diese Aktion erst wieder in {seconds} Sekunden ausführen.")
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
                    user = await self.bot.fetch_user(group_config['owner_id'])
                    if user:
                        course_msg += f" **@{user.name}#{user.discriminator}**"
                course_msg +=  f"\n       **↳** `!lg join {groupchannel.id}`"
            course_msg += "\n"

        msg += course_msg
        message = await channel.send(msg)
        if len(no_headers) > 0:
            support_channel = await self.bot.fetch_channel(int(self.support_channel))
            if support_channel:
                await support_channel.send(f"Es fehlen noch Überschriften für folgende Kurse in der Lerngruppenübersicht: **{', '.join(no_headers)}**")
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
                return False  # prevent api requests when nothing changed
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
                return False  # prevent api requests when nothing changed
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
        user = await self.bot.fetch_user(requested_channel_config["owner_id"])

        await channel.send(f":wave: <@!{user.id}>, hier ist deine neue Lerngruppe.\n"
                           "Es gibt offene und private Lerngruppen. Eine offene Lerngruppe ist für jeden sichtbar "
                           "und jeder kann darin schreiben. Eine private Lerngruppe ist unsichtbar und auf eine "
                           "Gruppe an Kommilitoninnen beschränkt."
                           "```"
                           "Besitzerinfunktionen:\n"
                           "!lg addmember <@newmember>: Fügt ein Mitglied zur Lerngruppe hinzu.\n"                           
                           "!lg owner <@newowner>: Ändert die Besitzerin der Lerngruppe auf @newowner.\n"
                           "!lg open: Öffnet eine Lerngruppe.\n"
                           "!lg close: Schließt eine Lerngruppe.\n"
                           "!lg private: Stellt die Lerngruppe auf privat.\n"
                           "!lg show: Zeigt eine private oder geschlossene Lerngruppe in der Lerngruppenliste an.\n"
                           "!lg hide: Entfernt eine private oder geschlossene Lerngruppe aus der Lerngruppenliste.\n"
                           "!lg kick <@user>: Schließt eine Benutzerin von der Lerngruppe aus.\n"   
                           "\nKommandos für alle:\n"
                           "!lg id: Zeigt die ID der Lerngruppe an mit der andere Kommilitoninnen beitreten können.\n"
                           "!lg members: Zeigt die Mitglieder der Lerngruppe an.\n"
                           "!lg owner: Zeigt die Besitzerin der Lerngruppe.\n"
                           "!lg leave: Du verlässt die Lerngruppe.\n"
                           "!lg join: Anfrage stellen in die Lerngruppe aufgenommen zu werden.\n"
                           "\nMit dem nachfolgenden Kommando kann eine Kommilitonin darum "
                           "bitten in die Lerngruppe aufgenommen zu werden wenn diese bereits privat ist.\n"
                           f"!lg join {channel.id}"
                            "\n(manche Kommandos sind von Discord limitiert und können nur einmal alle 5 Minuten ausgeführt werden)"
                           "```"
                           )
        self.groups["groups"][str(channel.id)] = {
            "owner_id": requested_channel_config["owner_id"],
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

    async def add_member_to_group(self, channel: disnake.TextChannel, arg_member: disnake.Member, send_message=True):
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
                                              "Dieser Link führt dich direkt zum Lerngruppen-Channel. " 
                                              "Diese Nachricht kannst du bei Bedarf in unserer Unterhaltung " 
                                              "über Rechtsklick anpinnen.")
                except:
                    pass

        group_config["users"] = users

        await self.save_groups()

    async def remove_member_from_group(self, channel: disnake.TextChannel, arg_member: disnake.Member, send_message=True):
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
                await utils.send_dm(user, f"Du wurdest aus der Lerngruppe {channel.name} entfernt")

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
            mods: disnake.PermissionOverwrite(read_messages=True),
            guild.default_role: disnake.PermissionOverwrite(read_messages=False)
        }

        if not group_config:
            return overwrites

        owner = self.bot.get_user(group_config["owner_id"])
        if not owner:
            return overwrites

        overwrites[owner] = disnake.PermissionOverwrite(read_messages=True)
        users = group_config.get("users")
        if not users:
            return overwrites

        for userid in users.keys():
            user = await self.bot.fetch_user(userid)
            overwrites[user] = disnake.PermissionOverwrite(read_messages=True)

        return overwrites

    @help(
        category="learninggroups",
        syntax="!lg <command>",
        brief="Lerngruppenverwaltung"
    )
    @commands.group(name="lg", aliases=["learninggroup", "lerngruppe"], pass_context=True)
    async def cmd_lg(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.channel.send("Gib `!help lg` ein um eine Übersicht über die Lerngruppen-Kommandos zu erhalten.")

    @help(
        command_group="lg",
        category="learninggroups",
        brief="Updated die Lerngruppenliste",
        mod=True
    )
    @cmd_lg.command(name="update")
    @commands.check(utils.is_mod)
    async def cmd_update(self, ctx):
        await self.update_channels()
        await self.update_statusmessage()

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg header <coursenumber> <name...>",
        brief="Fügt einen Kurs als neue Überschrift in Botys Lerngruppen-Liste (Kanal #lerngruppen) hinzu. "
              "Darf Leerzeichen enthalten, Anführungszeichen sind nicht erforderlich.",
        example="!lg header 1141 Mathematische Grundlagen",
        parameters={
            "coursenumber": "Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
            "name...": "Ein frei wählbarer Text (darf Leerzeichen enthalten).",
        },
        description="Kann auch zum Bearbeiten einer Überschrift genutzt werden. Bei bereits existierender "
                    "Kursnummer wird die Überschrift abgeändert",
        mod=True
    )
    @cmd_lg.command(name="header")
    @commands.check(utils.is_mod)
    async def cmd_add_header(self, ctx, arg_course, *arg_name):
        if not re.match(r"[0-9]+", arg_course):
            await ctx.channel.send(
                f"Fehler! Die Kursnummer muss numerisch sein. Gib `!help add-course` für Details ein.")
            return

        self.header[arg_course] = f"{arg_course} - {' '.join(arg_name)}"
        self.save_header()
        await self.update_statusmessage()

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg add <coursenumber> <name> <semester> <status> <@usermention>",
        example="!lg add 1142 mathegenies sose22 closed @someuser",
        brief="Fügt einen Lerngruppen-Kanal hinzu. Der Name darf keine Leerzeichen enthalten.",
        parameters={
            "coursenumber": "Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
            "name": "Ein frei wählbarer Text ohne Leerzeichen. Bindestriche sind zulässig.",
            "semester": ("Das Semester, für welches diese Lerngruppe erstellt werden soll."
                         "sose oder wise gefolgt von der zweistelligen Jahreszahl (z. B. sose22)."),
            "status": "Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed).",
            "@usermention": "Die so erwähnte Benutzerin wird als Besitzerin für die Lerngruppe gesetzt."
        },
        mod=True
    )
    @cmd_lg.command(name="add")
    @commands.check(utils.is_mod)
    async def cmd_add_group(self, ctx, arg_course, arg_name, arg_semester, arg_state, arg_owner: disnake.Member):
        state = self.arg_state_to_group_state(arg_state)
        channel_config = {"owner_id": arg_owner.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "state": state, "is_listed": False}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name):
            return

        self.groups["requested"][str(ctx.message.id)] = channel_config
        await self.save_groups()
        await self.add_requested_group_channel(ctx.message, direct=True)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg request <coursenumber> <name> <semester> <status>",
        brief="Stellt eine Anfrage für einen neuen Lerngruppen-Kanal.",
        example="!lg request 1142 mathegenies sose22 closed",
        description=("Moderatorinnen können diese Anfrage bestätigen, dann wird die Gruppe eingerichtet. "
                     "Die Besitzerin der Gruppe ist die Benutzerin die die Anfrage eingestellt hat."),
        parameters={
            "coursenumber": "Nummer des Kurses, wie von der FernUni angegeben (ohne führende Nullen z. B. 1142).",
            "name": "Ein frei wählbarer Text ohne Leerzeichen.",
            "semester": "Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt "
            "von der zweistelligen Jahreszahl (z. B. sose22).",
            "status": "Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed) oder ob es sich um eine private Lerngruppe handelt (private)."
        }
    )
    @cmd_lg.command(name="request", aliases=["r", "req"])
    async def cmd_request_group(self, ctx, arg_course, arg_name, arg_semester, arg_state):

        arg_state = re.sub(r"[^a-z0-9]", "", arg_state.lower())
        arg_semester = re.sub(r"[^a-z0-9]", "", arg_semester.lower())

        if re.match(r"(wise)|(sose)[0-9]+", arg_state) and re.match(r"(open)|(closed*)|(private)", arg_semester):
            tmp = arg_state
            arg_state = arg_semester
            arg_semester = tmp

        arg_semester = re.sub(r"[^wiseo0-9]", "", arg_semester)

        arg_state = re.sub(r"[^a-z]", "", arg_state)

        state = self.arg_state_to_group_state(arg_state)

        arg_course = re.sub(r"[^0-9]", "", arg_course)
        arg_course = re.sub(r"^0+", "", arg_course)

        arg_name = re.sub(
            r"[^A-Za-zäöüß0-9-]",
            "",
            arg_name.lower().replace(" ", "-")
        )




        if len(arg_semester) == 8:
            arg_semester = f"{arg_semester[0:4]}{arg_semester[-2:]}"
        channel_config = {"owner_id": ctx.author.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "state": state, "is_listed": False}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name):
            return

        channel = await self.bot.fetch_channel(int(self.channel_request))
        channel_name = self.full_channel_name(channel_config)

        message = await utils.confirm(
            channel=channel,
            title="Lerngruppenanfrage",
            description=f"<@!{ctx.author.id}> möchte gerne die Lerngruppe **#{channel_name}** eröffnen.",
            custom_prefix="learninggroups:group"
        )
        self.groups["requested"][str(message.id)] = channel_config
        await self.save_groups()

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg show",
        brief="Zeigt einen privaten Lerngruppenkanal trotzdem in der Liste an.",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Die Lerngruppe wird in der Übersicht der Lerngruppen gelistet, so können Kommilitoninnen noch "
                     "Anfragen stellen, um in die Lerngruppe aufgenommen zu werden."
                     "Diese Aktion kann nur von der Besitzerin der Lerngruppe ausgeführt werden. ")
    )
    @cmd_lg.command(name="show")
    async def cmd_show(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            channel_config = self.channels[str(ctx.channel.id)]
            if channel_config:
                if channel_config.get("state") == GroupState.PRIVATE:
                    if await self.set_channel_listing(ctx.channel, True):
                        await ctx.channel.send("Die Lerngruppe wird nun in der Lerngruppenliste angezeigt.")
                elif channel_config.get("state") == GroupState.OPEN:
                    await ctx.channel.send("Nichts zu tun. Offene Lerngruppen werden sowieso in der Liste angezeigt.")
                elif channel_config.get("state") == GroupState.CLOSED:
                    await ctx.channel.send("Möchtest du die Gruppen öffnen? Versuch‘s mit `!lg open`")


    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg hide",
        brief="Versteckt einen privaten Lerngruppenkanal. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Die Lerngruppe wird nicht mehr in der Liste der Lerngruppen aufgeführt. "
                     "Diese Aktion kann nur von der Besitzerin der Lerngruppe ausgeführt werden. ")
    )
    @cmd_lg.command(name="hide")
    async def cmd_hide(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            channel_config = self.channels[str(ctx.channel.id)]
            if channel_config:
                if channel_config.get("state") == GroupState.PRIVATE:
                    if await self.set_channel_listing(ctx.channel, False):
                        await ctx.channel.send("Die Lerngruppe wird nun nicht mehr in der Lerngruppenliste angezeigt.")
                    return

                elif channel_config.get("state") == GroupState.OPEN:
                    await ctx.channel.send("Offene Lerngruppen können nicht aus der Lerngruppenliste entfernt werden. " 
                                           "Führe `!lg close` aus um die Lerngruppe zu schließen, "
                                           "oder `!lg private` um diese auf "
                                           "privat zu schalten.")
                elif channel_config.get("state") == GroupState.CLOSED:
                    await ctx.channel.send("Wenn diese Gruppe privat werden soll, ist das Kommando das du brauchst: `!lg private`")

    @cmd_lg.command(name="debug")
    @commands.check(utils.is_mod)
    async def cmd_debug(self, ctx):
        channel_config = self.channels[str(ctx.channel.id)]
        if not channel_config:
            await ctx.channel.send("None")
            return
        await ctx.channel.send(str(channel_config))


    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg open",
        brief="Öffnet den Lerngruppen-Kanal wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Verschiebt den Lerngruppen-Kanal in die Kategorie für offene Kanäle und ändert das Icon. "
                     "Diese Aktion kann nur von der Besitzerin der Lerngruppe ausgeführt werden. ")
    )
    @cmd_lg.command(name="open", aliases=["opened", "offen"])
    async def cmd_open(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, state=GroupState.OPEN)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg close",
        brief="Schließt den Lerngruppen-Kanal wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Stellt die Lerngruppe auf geschlossen. Dies ist rein symbolisch und zeigt an, "
                     "dass keine neuen Mitglieder mehr aufgenommen werden. "
                     "Diese Aktion kann nur von der Besitzerin der Lerngruppe ausgeführt werden. ")
    )
    @cmd_lg.command(name="close", aliases=["closed", "geschlossen"])
    async def cmd_close(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, state=GroupState.CLOSED)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg private",
        brief="Macht aus deiner Lerngruppe eine private Lerngruppe wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Stellt die Lerngruppe auf privat. Es haben nur noch Mitglieder "
                     "der Lerngruppe zugriff auf den Kanal. (siehe `!lg members`)"
                     "Diese Aktion kann nur von der Besitzerin der Lerngruppe ausgeführt werden. ")
    )
    @cmd_lg.command(name="private", aliases=["privat"])
    async def cmd_private(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            if await self.set_channel_state(ctx.channel, state=GroupState.PRIVATE):
                await self.update_permissions(ctx.channel)



    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg rename <name>",
        brief="Ändert den Namen des Lerngruppen-Kanals, in dem das Komando ausgeführt wird.",
        example="!lg rename matheluschen",
        description="Aus #1142-matheprofis-sose22 wird nach dem Aufruf des Beispiels #1142-matheluschen-sose22.",
        parameters={
            "name": "Der neue Name der Lerngruppe ohne Leerzeichen."
        },
        mod=True
    )
    @cmd_lg.command(name="rename")
    @commands.check(utils.is_mod)
    async def cmd_rename(self, ctx, arg_name):
        await self.set_channel_name(ctx.channel, arg_name)

    @help(
        command_group="lg",
        syntax="!lg archive",
        category="learninggroups",
        brief="Archiviert den Lerngruppen-Kanal",
        description="Verschiebt den Lerngruppen-Kanal, in welchem dieses Kommando ausgeführt wird, ins Archiv.",
        mod=True
    )
    @cmd_lg.command(name="archive", aliases=["archiv"])
    @commands.check(utils.is_mod)
    async def cmd_archive(self, ctx):
        await self.archive(ctx.channel)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg owner <@usermention>",
        example="!owner @someuser",
        brief="Setzt die Besitzerin eines Lerngruppen-Kanals",
        description="Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. ",
        parameters={
            "@usermention": "Die neue Besitzerin der Lerngruppe."
        }
    )
    @cmd_lg.command(name="owner")
    async def cmd_owner(self, ctx, new_owner: disnake.Member = None):
        group_config = self.groups["groups"].get(str(ctx.channel.id))

        if not group_config:
            self.groups["groups"][str(ctx.channel.id)] = {}
            group_config = self.groups["groups"][str(ctx.channel.id)]

        owner_id = group_config.get("owner_id")

        if not owner_id:
            return

        if not new_owner:
                user = await self.bot.fetch_user(owner_id)
                await ctx.channel.send(f"Besitzerin: @{user.name}#{user.discriminator}")

        elif isinstance(group_config, dict):
            owner = await self.bot.fetch_user(owner_id)
            if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
                group_config["owner_id"] = new_owner.id
                await self.remove_member_from_group(ctx.channel, new_owner, False)
                if new_owner != owner:
                    await self.add_member_to_group(ctx.channel, owner, False)
                await self.save_groups()
                await self.update_permissions(ctx.channel)
                await ctx.channel.send(
                    f"Glückwunsch {new_owner.mention}! Du bist jetzt die Besitzerin dieser Lerngruppe.")

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg addmember <@usermention> <#channel>",
        example="!lg addmember @someuser #1141-mathegl-lerngruppe-sose21",
        brief="Fügt eine Benutzerin zu einer Lerngruppe hinzu.",
        parameters={
            "@usermention": "Die so erwähnte Benutzerin wird zur Lerngruppe hinzugefügt.",
            "#channel": "(optional) Der Kanal dem die Benutzerin hinzugefügt werden soll."
        }
    )
    @cmd_lg.command(name="addmember", aliases=["addm", "am"])
    async def cmd_add_member(self, ctx, arg_member: disnake.Member, arg_channel: disnake.TextChannel = None):
        if not arg_channel:
            if not self.channels.get(str(ctx.channel.id)):
                await ctx.channel.send("Wenn das Kommando außerhalb eines Lerngruppenkanals aufgerufen wird, muss der" 
                                       "Lerngruppenkanal angehängt werden. `!lg addmember <@usermention> <#channel>`")
                return
            arg_channel = ctx.channel
        if self.is_group_owner(arg_channel, ctx.author) or utils.is_mod(ctx):
            await self.add_member_to_group(arg_channel, arg_member)
            await self.update_permissions(arg_channel)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg removemember <@usermention> <#channel>",
        example="!lg removemember @someuser #1141-mathegl-lerngruppe-sose21",
        brief="Entfernt eine Benutzerin aus einer Lerngruppe.",
        parameters={
            "#channel": "Der Kanal aus dem die Benutzerin gelöscht werden soll.",
            "@usermention": "Die so erwähnte Benutzerin wird aus der Lerngruppe entfernt."
        },
        mod=True
    )
    @cmd_lg.command(name="removemember", aliases=["remm", "rm"])
    @commands.check(utils.is_mod)
    async def cmd_remove_member(self, ctx, arg_member: disnake.Member, arg_channel: disnake.TextChannel):
        await self.remove_member_from_group(arg_channel, arg_member)
        await self.update_permissions(arg_channel)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg members",
        brief="Listet die Mitglieder der Lerngruppe auf.",
    )
    @cmd_lg.command(name="members")
    async def cmd_members(self, ctx):
        group_config = self.groups["groups"].get(str(ctx.channel.id))
        if not group_config:
            await ctx.channel.send("Das ist kein Lerngruppenkanal.")
            return
        owner_id = group_config.get("owner_id")

        if not owner_id:
            return

        owner = await self.bot.fetch_user(owner_id)
        users = group_config.get("users", {})
        if not users and not owner:
            await ctx.channel.send("Keine Lerngruppenmitglieder vorhanden.")
            return

        names = []

        for user_id in users:
            user = await self.bot.fetch_user(user_id)
            names.append("@" + user.name + "#" + user.discriminator)

        await ctx.channel.send(f"Besitzerin: **@{owner.name}#{owner.discriminator}**\nMitglieder: " +
                               (f"{', '.join(names)}" if len(names) > 0 else "Keine"))

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg id",
        brief="Zeigt die ID für deine Lerngruppe an.",
    )
    @cmd_lg.command(name="id")
    async def cmd_id(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            group_config = self.groups["groups"].get(str(ctx.channel.id))
            if not group_config:
                await ctx.channel.send("Das ist kein Lerngruppenkanal.")
                return
        await ctx.channel.send(f"Die ID dieser Lerngruppe lautet: `{str(ctx.channel.id)}`.\n"
                               f"Beitrittsanfrage mit: `!lg join {str(ctx.channel.id)}`")

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg join <lg-id>",
        brief="Fragt bei der Besitzerin einer Lerngruppe um Aufnahme.",
        parameters={
            "id": "Die ID zur Lerngruppe."
        }
    )
    @cmd_lg.command(name="join")
    async def cmd_join(self, ctx, arg_id_or_channel: Union[int, disnake.TextChannel] = None):

        if arg_id_or_channel is None:
            arg_id_or_channel = ctx.channel

        cid = arg_id_or_channel.id if type(arg_id_or_channel) is disnake.TextChannel else arg_id_or_channel

        group_config = self.groups["groups"].get(str(cid))
        if not group_config:
            await ctx.channel.send("Das ist keine gültiger Lerngruppenkanal.")
            return

        channel = await self.bot.fetch_channel(int(cid))

        await utils.confirm(
            channel=channel,
            title="Jemand möchte deiner Lerngruppe beitreten!",
            description=f"<@!{ctx.author.id}> möchte gerne der Lerngruppe **#{channel.name}** beitreten.",
            message=f"<@!{group_config['owner_id']}>, du wirst gebraucht. Anfrage von <@!{ctx.author.id}>:",
            custom_prefix="learninggroups:join"
        )
        await utils.send_dm(ctx.author, f"Deine Anfrage wurde an **#{channel.name}** gesendet. "
                                        "Sobald die Besitzerin der Lerngruppe darüber "
                                        "entschieden hat bekommst du Bescheid.")

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg kick <@usermention>",
        brief="Wirft @usermention aus der Gruppe."
    )
    @cmd_lg.command(name="kick")
    async def cmd_kick(self, ctx, arg_member: disnake.Member):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            group_config = self.groups["groups"].get(str(ctx.channel.id))
            if not group_config:
                await ctx.channel.send("Das ist keine gültiger Lerngruppenkanal.")
                return

            await self.remove_member_from_group(ctx.channel, arg_member)
            await self.update_permissions(ctx.channel)

    @help(
        command_group="lg",
        category="learninggroups",
        syntax="!lg leave",
        brief="Du verlässt die Lerngruppe."
    )
    @cmd_lg.command(name="leave")
    async def cmd_leave(self, ctx):
        group_config = self.groups["groups"].get(str(ctx.channel.id))
        if not group_config:
            await ctx.channel.send("Das ist keine gültiger Lerngruppenkanal.")
            return

        if group_config["owner_id"] == ctx.author.id:
            await ctx.channel.send("Du kannst nicht aus deiner eigenen Lerngruppe flüchten. Übertrage erst den Besitz.")
            return

        await self.remove_member_from_group(ctx.channel, ctx.author)
        await self.update_permissions(ctx.channel)

    async def on_group_request(self, confirmed, button, interaction: InteractionMessage):
        channel = interaction.channel
        member = interaction.author
        message = interaction.message

        if str(channel.id) == str(self.channel_request):
            request = self.groups["requested"].get(str(message.id))
            if confirmed and self.is_mod(member):
                await self.add_requested_group_channel(message, direct=False)

            elif not confirmed and (self.is_request_owner(request, member) or self.is_mod(member)):
                if self.is_mod(member):
                    user = await self.bot.fetch_user(request["owner_id"] )
                    if user:
                        await utils.send_dm(user, f"Deine Lerngruppenanfrage für #{self.full_channel_name(request)} wurde abgelehnt.")
                await self.remove_group_request(message)

                await message.delete()

    async def on_join_request(self, confirmed, button, interaction: InteractionMessage):
        channel = interaction.channel
        member = interaction.author
        message = interaction.message
        group_config = self.groups["groups"].get(str(channel.id))

        if not group_config:
            return

        if self.is_group_owner(channel, member) or self.is_mod(member):
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

    async def cog_command_error(self, ctx, error):
        try:
            await handle_error(ctx, error)
        except:
            pass

