<<<<<<< HEAD
import json
import os
import re
import time

import disnake
from disnake.ext import commands

import utils
from cogs.help import help, handle_error, help_category

"""
  Environment Variablen:
  DISCORD_LEARNINGGROUPS_OPEN - ID der Kategorie für offene Lerngruppen
  DISCORD_LEARNINGGROUPS_CLOSE - ID der Kategorie für geschlossene Lerngruppen
  DISCORD_LEARNINGGROUPS_ARCHIVE - ID der Kategorie für archivierte Lerngruppen
  DISCORD_LEARNINGGROUPS_REQUEST - ID des Channels in welchem Requests vom Bot eingestellt werden
  DISCORD_LEARNINGGROUPS_INFO - ID des Channels in welchem die Lerngruppen-Informationen gepostet/aktualisert werden
  DISCORD_LEARNINGGROUPS_FILE - Name der Datei mit Verwaltungsdaten der Lerngruppen (minimaler Inhalt: {"requested": {},"groups": {}})
  DISCORD_LEARNINGGROUPS_COURSE_FILE - Name der Datei welche die Kursnamen für die Lerngruppen-Informationen enthält (minimalter Inhalt: {})
  DISCORD_MOD_ROLE - ID der Moderator Rolle von der erweiterte Lerngruppen-Actionen ausgeführt werden dürfen
"""


@help_category("learninggroups", "Lerngruppen",
               "Mit dem Lerngruppen-Feature kannst du Lerngruppen-Kanäle beantragen und/oder diese rudimentär verwalten.",
               "Hier kannst du Lerngruppen-Kanäle anlegen, beantragen und verwalten.")
class LearningGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ratelimit 2 in 10 minutes (305 * 2 = 610 = 10 minutes and 10 seconds)
        self.rename_ratelimit = 305
        self.msg_max_len = 2000
        self.category_open = os.getenv('DISCORD_LEARNINGGROUPS_OPEN')
        self.category_close = os.getenv('DISCORD_LEARNINGGROUPS_CLOSE')
        self.category_archive = os.getenv('DISCORD_LEARNINGGROUPS_ARCHIVE')
        self.channel_request = os.getenv('DISCORD_LEARNINGGROUPS_REQUEST')
        self.channel_info = os.getenv('DISCORD_LEARNINGGROUPS_INFO')
        self.group_file = os.getenv('DISCORD_LEARNINGGROUPS_FILE')
        self.header_file = os.getenv('DISCORD_LEARNINGGROUPS_COURSE_FILE')
        self.mod_role = os.getenv("DISCORD_MOD_ROLE")
        self.groups = {}
        self.header = {}
        self.load_groups()
        self.load_header()

    def load_header(self):
        file = open(self.header_file, mode='r')
        self.header = json.load(file)

    def save_header(self):
        file = open(self.header_file, mode='w')
        json.dump(self.header, file)

    def load_groups(self):
        group_file = open(self.group_file, mode='r')
        self.groups = json.load(group_file)

    def save_groups(self):
        group_file = open(self.group_file, mode='w')
        json.dump(self.groups, group_file)

    def arg_open_to_bool(self, arg_open):
        if arg_open in ["offen", "open"]:
            return True
        if arg_open in ["geschlossen", "closed", "close"]:
            return False
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
        if channel_config['is_open'] is None:
            if command:
                await ctx.channel.send(
                    f"Fehler! Bitte gib an ob die Gruppe **offen** (**open**) oder **geschlossen** (**closed**) ist. Gib `!help {command}` für Details ein.")
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
            await channel.send(f"Fehler! Du kannst diese Aktion erst wieder in {seconds} Sekunden ausführen.")
        return seconds > 0

    async def category_of_channel(self, is_open):
        category_to_fetch = self.category_open if is_open else self.category_close
        category = await self.bot.fetch_channel(category_to_fetch)
        return category

    def full_channel_name(self, channel_config):
        return (f"{f'🌲' if channel_config['is_open'] else f'🛑'}"
                f"{channel_config['course']}-{channel_config['name']}-{channel_config['semester']}")

    async def update_groupinfo(self):
        info_message_ids = self.groups.get("messageids")
        channel = await self.bot.fetch_channel(int(self.channel_info))

        for info_message_id in info_message_ids:
            message = await channel.fetch_message(info_message_id)
            await message.delete()

        info_message_ids = []

        msg = f"**Lerngruppen**\n\n"
        course_msg = ""
        sorted_groups = sorted(self.groups["groups"].values(
        ), key=lambda group: f"{group['course']}-{group['name']}")
        open_groups = [group for group in sorted_groups if group['is_open']]
        courseheader = None
        for group in open_groups:

            if group['course'] != courseheader:
                if len(msg) + len(course_msg) > self.msg_max_len:
                    message = await channel.send(msg)
                    info_message_ids.append(message.id)
                    msg = course_msg
                    course_msg = ""
                else:
                    msg += course_msg
                    course_msg = ""
                header = self.header.get(group['course'])
                if header:
                    course_msg += f"**{header}**\n"
                else:
                    course_msg += f"**{group['course']} - -------------------------------------**\n"
                courseheader = group['course']

            groupchannel = await self.bot.fetch_channel(int(group['channel_id']))
            course_msg += f"    {groupchannel.mention}\n"

        msg += course_msg
        message = await channel.send(msg)
        info_message_ids.append(message.id)
        self.groups["messageids"] = info_message_ids
        self.save_groups()

    async def archive(self, channel):
        category = await self.bot.fetch_channel(self.category_archive)
        await self.move_channel(channel, category)
        await channel.edit(name=f"archiv-${channel.name[1:]}")
        self.remove_group(channel)

    async def set_channel_state(self, channel, is_open):
        channel_config = self.groups["groups"][str(channel.id)]
        if await self.check_rename_rate_limit(channel_config):
            return  # prevent api requests when ratelimited

        was_open = channel_config["is_open"]
        if (was_open == is_open):
            return  # prevent api requests when nothing changed

        channel_config["is_open"] = is_open
        channel_config["last_rename"] = int(time.time())

        await channel.edit(name=self.full_channel_name(channel_config))
        category = await self.category_of_channel(is_open)
        await self.move_channel(channel, category)
        await self.update_groupinfo()
        self.save_groups()

    async def set_channel_name(self, channel, name):
        channel_config = self.groups["groups"][str(channel.id)]

        if await self.check_rename_rate_limit(channel_config):
            return  # prevent api requests when ratelimited

        channel_config["name"] = name
        channel_config["last_rename"] = int(time.time())

        await channel.edit(name=self.full_channel_name(channel_config))
        await self.update_groupinfo()
        self.save_groups()

    async def move_channel(self, channel, category):
        for sortchannel in category.text_channels:
            if sortchannel.name[1:] > channel.name[1:]:
                await channel.move(category=category, before=sortchannel, sync_permissions=True)
                return
        await channel.move(category=category, sync_permissions=True, end=True)

    async def add_requested_group_channel(self, message, direct=False):
        channel_config = self.groups["requested"].get(str(message.id))

        category = await self.category_of_channel(channel_config["is_open"])
        channel_name = self.full_channel_name(channel_config)
        channel = await category.create_text_channel(channel_name)
        channel_config["channel_id"] = str(channel.id)

        user = await self.bot.fetch_user(channel_config["owner_id"])
        await utils.send_dm(user,
                            f"Deine Lerngruppe <#{channel.id}> wurde eingerichtet. Du kannst mit **!open** und **!close** den Status dieser Gruppe setzen. Bedenke aber bitte, dass die Discord API die möglichen Namensänderungen stark limitiert. Daher ist nur ein Statuswechsel alle **5 Minuten** möglich.")

        self.groups["groups"][str(channel.id)] = channel_config

        self.remove_group_request(message)
        if not direct:
            await message.delete()

        await self.update_groupinfo()
        self.save_groups()

    def remove_group_request(self, message):
        del self.groups["requested"][str(message.id)]
        self.save_groups()

    def remove_group(self, channel):
        del self.groups["groups"][str(channel.id)]
        self.save_groups()

    @help(
        category="learninggroups",
        brief="Erstellt aus den Lerngruppen-Kanälen eine Datendatei. ",
        description=(
                "Initialisiert alle Gruppen in den Kategorien für offene und geschlossene Lerngruppen und baut die Verwaltungsdaten dazu auf. "
                "Die Lerngruppen-Kanal-Namen müssen hierfür zuvor ins Format #{symbol}{kursnummer}-{name}-{semester} gebracht werden. "
                "Als Owner wird der ausführende Account für alle Lerngruppen gesetzt. "
                "Wenn die Verwaltungsdatenbank nicht leer ist, wird das Kommando nicht ausgeführt. "
        ),
        mod=True
    )
    @commands.command(name="init-groups")
    @commands.check(utils.is_mod)
    async def cmd_init_groups(self, ctx):
        if len(self.groups["groups"]) > 0:
            await ctx.channel.send("Nope. Das sollte ich lieber nicht tun.")
            return

        msg = "Initialisierung abgeschlossen:\n"
        for is_open in [True, False]:
            category = await self.category_of_channel(is_open)
            msg += f"**{category.name}**\n"

            for channel in category.text_channels:
                result = re.match(
                    r"([0-9]{4,6})-(.*)-([a-z0-9]+)$", channel.name[1:])
                if result is None:
                    await utils.send_dm(ctx.author, f"Abbruch! Channelname hat falsches Format: {channel.name}")
                    self.groups["groups"] = {}
                    return

                course, name, semester = result.group(1, 2, 3)

                channel_config = {"owner_id": ctx.author.id, "course": course, "name": name, "semester": semester,
                                  "is_open": is_open, "channel_id": str(channel.id)}
                if not await self.is_channel_config_valid(ctx, channel_config):
                    await utils.send_dm(ctx.author, f"Abbruch! Channelname hat falsches Format: {channel.name}")
                    self.groups["groups"] = {}
                    return

                self.groups["groups"][str(channel.id)] = channel_config
                msg += f"   #{course}-{name}-{semester}\n"

        await utils.send_dm(ctx.author, msg)
        await self.update_groupinfo()
        self.save_groups()

    @help(
        category="learninggroups",
        syntax="!add-course <coursenumber> <name...>",
        brief="Fügt einen Kurs als neue Überschrift in Botys Lerngruppen-Liste (Kanal #lerngruppen) hinzu. Darf Leerzeichen enthalten, Anführungszeichen sind nicht erforderlich.",
        example="!add-course 1141 Mathematische Grundlagen",
        parameters={
            "coursenumber": "Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
            "name...": "Ein frei wählbarer Text (darf Leerzeichen enthalten).",
        },
        description="Kann auch zum Bearbeiten einer Überschrift genutzt werden. Bei bereits existierender Kursnummer wird die Überschrift abgeändert",
        mod=True
    )
    @commands.command(name="add-course")
    @commands.check(utils.is_mod)
    async def cmd_add_course(self, ctx, arg_course, *arg_name):
        if not re.match(r"[0-9]+", arg_course):
            await ctx.channel.send(
                f"Fehler! Die Kursnummer muss numerisch sein. Gib `!help add-course` für Details ein.")
            return

        self.header[arg_course] = f"{arg_course} - {' '.join(arg_name)}"
        self.save_header()
        await self.update_groupinfo()

    @help(
        category="learninggroups",
        syntax="!add-group <coursenumber> <name> <semester> <status> <@usermention>",
        example="!add-group 1142 mathegenies sose22 clsoed @someuser",
        brief="Fügt einen Lerngruppen-Kanal hinzu. Der Name darf keine Leerzeichen enthalten.",
        parameters={
            "coursenumber": "Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
            "name": "Ein frei wählbarer Text ohne Leerzeichen. Bindestriche sind zulässig.",
            "semester": "Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der zweistelligen Jahreszahl (z. B. sose22).",
            "status": "Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed).",
            "@usermention": "Der so erwähnte Benutzer wird als Besitzer für die Lerngruppe gesetzt."
        },
        mod=True
    )
    @commands.command(name="add-group")
    @commands.check(utils.is_mod)
    async def cmd_add_group(self, ctx, arg_course, arg_name, arg_semester, arg_open, arg_owner: disnake.Member):
        is_open = self.arg_open_to_bool(arg_open)
        channel_config = {"owner_id": arg_owner.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "is_open": is_open}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name):
            return

        self.groups["requested"][str(ctx.message.id)] = channel_config
        self.save_groups()
        await self.add_requested_group_channel(ctx.message, direct=True)

    @help(
        category="learninggroups",
        syntax="!request-group <coursenumber> <name> <semester> <status>",
        brief="Stellt eine Anfrage für einen neuen Lerngruppen-Kanal.",
        example="!request-group 1142 mathegenies sose22 closed",
        description=("Moderatorinnen können diese Anfrage bestätigen, dann wird die Gruppe eingerichtet. "
                     "Der Besitzer der Gruppe ist der Benutzer der die Anfrage eingestellt hat."),
        parameters={
            "coursenumber": "Nummer des Kurses, wie von der FernUni angegeben (ohne führende Nullen z. B. 1142).",
            "name": "Ein frei wählbarer Text ohne Leerzeichen.",
            "semester": "Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der zweistelligen Jahrenszahl (z. B. sose22).",
            "status": "Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed)."
        }
    )
    @commands.command(name="request-group")
    async def cmd_request_group(self, ctx, arg_course, arg_name, arg_semester, arg_open):
        is_open = self.arg_open_to_bool(arg_open)
        channel_config = {"owner_id": ctx.author.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "is_open": is_open}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name):
            return

        channel_name = self.full_channel_name(channel_config)
        embed = disnake.Embed(title="Lerngruppenanfrage!",
                              description=f"<@!{ctx.author.id}> möchte gerne die Lerngruppe **#{channel_name}** eröffnen",
                              color=19607)

        channel_request = await self.bot.fetch_channel(int(self.channel_request))
        message = await channel_request.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")

        self.groups["requested"][str(message.id)] = channel_config
        self.save_groups()

    @help(
        category="learninggroups",
        brief="Öffnet den Lerngruppen-Kanal wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Verschiebt den Lerngruppen-Kanal in die Kategorie für offene Kanäle und ändert das Icon. "
                     "Diese Aktion kann nur vom Besitzer der Lerngruppe ausgeführt werden. ")
    )
    @commands.command(name="open")
    async def cmd_open(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, is_open=True)

    @help(
        category="learninggroups",
        brief="Schließt den Lerngruppen-Kanal wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Verschiebt den Lerngruppen-Kanal in die Kategorie für geschlossene Kanäle und ändert das Icon. "
                     "Diese Aktion kann nur vom Besitzer der Lerngruppe ausgeführt werden. ")
    )
    @commands.command(name="close")
    async def cmd_close(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, is_open=False)

    @help(
        category="learninggroups",
        syntax="!rename <name>",
        brief="Ändert den Namen des Lerngruppen-Kanals, in dem das Komando ausgeführt wird.",
        example="!rename matheluschen",
        description="Aus #1142-matheprofis-sose22 wird nach dem Aufruf des Beispiels #1142-matheluschen-sose22.",
        parameters={
            "name": "Der neue Name der Lerngruppe ohne Leerzeichen."
        },
        mod=True
    )
    @commands.command(name="rename")
    @commands.check(utils.is_mod)
    async def cmd_rename(self, ctx, arg_name):
        await self.set_channel_name(ctx.channel, arg_name)

    @help(
        category="learninggroups",
        brief="Archiviert den Lerngruppen-Kanal",
        description="Verschiebt den Lerngruppen-Kanal, in welchem dieses Kommando ausgeführt wird, ins Archiv.",
        mod=True
    )
    @commands.command(name="archive")
    @commands.check(utils.is_mod)
    async def cmd_archive(self, ctx):
        await self.archive(ctx.channel)

    @help(
        category="learninggroups",
        syntax="!owner <@usermention>",
        example="!owner @someuser",
        brief="Setzt die Besitzerin eines Lerngruppen-Kanals",
        description="Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. ",
        parameters={
            "@usermention": "Der neue Besitzer der Lerngruppe."
        },
        mod=True
    )
    @commands.command(name="owner")
    @commands.check(utils.is_mod)
    async def cmd_owner(self, ctx, arg_owner: disnake.Member):
        channel_config = self.groups["groups"].get(str(ctx.channel.id))
        if channel_config:
            channel_config["owner_id"] = arg_owner.id
            self.save_groups()
            await ctx.channel.send(f"Glückwunsch {arg_owner.mention}! Du bist jetzt die Besitzerin dieser Lerngruppe.")

    @help(
        category="learninggroups",
        brief="Zeigt die Besitzerin eines Lerngruppen-Kanals an.",
        description="Muss im betreffenden Lerngruppen-Kanal ausgeführt werden.",
        mod=True
    )
    @commands.command(name="show-owner")
    @commands.check(utils.is_mod)
    async def cmd_show_owner(self, ctx):
        channel_config = self.groups["groups"].get(str(ctx.channel.id))
        owner_id = channel_config.get("owner_id")
        if owner_id:
            user = await self.bot.fetch_user(owner_id)
            await ctx.channel.send(f"Besitzer: @{user.name}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        request = self.groups["requested"].get(str(message.id))

        if payload.emoji.name in ["👍"] and self.is_group_request_message(message) and self.is_mod(payload.member):
            await self.add_requested_group_channel(message, direct=False)

        if payload.emoji.name in ["🗑️"] and self.is_group_request_message(message) and (
                self.is_request_owner(request, payload.member) or self.is_mod(payload.member)):
            self.remove_group_request(message)
            await message.delete()

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
=======
import json
import os
import re
import time

import discord
from discord.ext import commands

import utils
from cogs.help import help, handle_error, help_category

"""
  Environment Variablen:
  DISCORD_LEARNINGGROUPS_OPEN - ID der Kategorie für offene Lerngruppen
  DISCORD_LEARNINGGROUPS_CLOSE - ID der Kategorie für geschlossene Lerngruppen
  DISCORD_LEARNINGGROUPS_ARCHIVE - ID der Kategorie für archivierte Lerngruppen
  DISCORD_LEARNINGGROUPS_REQUEST - ID des Channels in welchem Requests vom Bot eingestellt werden
  DISCORD_LEARNINGGROUPS_INFO - ID des Channels in welchem die Lerngruppen-Informationen gepostet/aktualisert werden
  DISCORD_LEARNINGGROUPS_FILE - Name der Datei mit Verwaltungsdaten der Lerngruppen (minimaler Inhalt: {"requested": {},"groups": {}})
  DISCORD_LEARNINGGROUPS_COURSE_FILE - Name der Datei welche die Kursnamen für die Lerngruppen-Informationen enthält (minimalter Inhalt: {})
  DISCORD_MOD_ROLE - ID der Moderator Rolle von der erweiterte Lerngruppen-Actionen ausgeführt werden dürfen
"""

LG_OPEN_SYMBOL = f'🌲'
LG_CLOSE_SYMBOL = f'🛑'

@help_category("learninggroups", "Lerngruppen",
               "Mit dem Lerngruppen-Feature kannst du Lerngruppen-Kanäle beantragen und/oder diese rudimentär verwalten.",
               "Hier kannst du Lerngruppen-Kanäle anlegen, beantragen und verwalten.")
class LearningGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ratelimit 2 in 10 minutes (305 * 2 = 610 = 10 minutes and 10 seconds)
        self.rename_ratelimit = 305
        self.msg_max_len = 2000
        self.category_open = os.getenv('DISCORD_LEARNINGGROUPS_OPEN')
        self.category_close = os.getenv('DISCORD_LEARNINGGROUPS_CLOSE')
        self.category_archive = os.getenv('DISCORD_LEARNINGGROUPS_ARCHIVE')
        self.channel_request = os.getenv('DISCORD_LEARNINGGROUPS_REQUEST')
        self.channel_info = os.getenv('DISCORD_LEARNINGGROUPS_INFO')
        self.group_file = os.getenv('DISCORD_LEARNINGGROUPS_FILE')
        self.header_file = os.getenv('DISCORD_LEARNINGGROUPS_COURSE_FILE')
        self.mod_role = os.getenv("DISCORD_MOD_ROLE")
        self.guild_id = os.getenv("DISCORD_GUILD")
        self.groups = {}  #owner and learninggroup-member ids
        self.channels = {} #complete channel configs
        self.header = {} #headlines for statusmessage
        self.load_groups()
        self.load_header()

    @commands.Cog.listener(name="on_ready")
    async def on_ready(self):
        print("Dooing")
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

    async def save_groups(self):
        await self.update_channels()
        group_file = open(self.group_file, mode='w')
        json.dump(self.groups, group_file)

    def arg_open_to_bool(self, arg_open):
        if arg_open in ["offen", "open"]:
            return True
        if arg_open in ["geschlossen", "closed", "close"]:
            return False
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
        if channel_config['is_open'] is None:
            if command:
                await ctx.channel.send(
                    f"Fehler! Bitte gib an ob die Gruppe **offen** (**open**) oder **geschlossen** (**closed**) ist. Gib `!help {command}` für Details ein.")
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
            await channel.send(f"Fehler! Du kannst diese Aktion erst wieder in {seconds} Sekunden ausführen.")
        return seconds > 0

    async def category_of_channel(self, is_open):
        category_to_fetch = self.category_open if is_open else self.category_close
        category = await self.bot.fetch_channel(category_to_fetch)
        return category

    def full_channel_name(self, channel_config):
        return (f"{f'🌲' if channel_config['is_open'] else f'🛑'}"
                f"{channel_config['course']}-{channel_config['name']}-{channel_config['semester']}")

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
        open_channels = [channel for channel in sorted_channels if channel['is_open']]
        courseheader = None
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
                courseheader = lg_channel['course']

            groupchannel = await self.bot.fetch_channel(int(lg_channel['channel_id']))
            course_msg += f"    {groupchannel.mention}\n"

        msg += course_msg
        message = await channel.send(msg)
        info_message_ids.append(message.id)
        self.groups["messageids"] = info_message_ids
        await self.save_groups()

    async def archive(self, channel):
        category = await self.bot.fetch_channel(self.category_archive)
        await self.move_channel(channel, category)
        await channel.edit(name=f"archiv-${channel.name[1:]}")
        await self.remove_group(channel)

    async def set_channel_state(self, channel, is_open):
        channel_config = self.channels[str(channel.id)]
        if await self.check_rename_rate_limit(channel_config):
            return  # prevent api requests when ratelimited

        was_open = channel_config["is_open"]
        if (was_open == is_open):
            return  # prevent api requests when nothing changed

        self.groups["groups"][str(channel.id)]["last_rename"] = int(time.time())

        await channel.edit(name=self.full_channel_name(channel_config))
        category = await self.category_of_channel(is_open)
        await self.move_channel(channel, category)
        await self.save_groups()
        await self.update_statusmessage()

    async def set_channel_name(self, channel, name):
        channel_config = self.channels[str(channel.id)]

        if await self.check_rename_rate_limit(channel_config):
            return  # prevent api requests when ratelimited

        self.groups["groups"][str(channel.id)]["last_rename"] = int(time.time())
        channel_config["name"] = name

        await channel.edit(name=self.full_channel_name(channel_config))
        await self.save_groups()
        await self.update_statusmessage()

    async def move_channel(self, channel, category):
        for sortchannel in category.text_channels:
            if sortchannel.name[1:] > channel.name[1:]:
                await channel.move(category=category, before=sortchannel, sync_permissions=True)
                return
        await channel.move(category=category, sync_permissions=True, end=True)

    async def add_requested_group_channel(self, message, direct=False):
        requested_channel_config = self.groups["requested"].get(str(message.id))

        category = await self.category_of_channel(requested_channel_config["is_open"])
        full_channel_name = self.full_channel_name(requested_channel_config)
        channel = await category.create_text_channel(full_channel_name)
        user = await self.bot.fetch_user(requested_channel_config["owner_id"])
        await utils.send_dm(user,
                            f"Deine Lerngruppe <#{channel.id}> wurde eingerichtet. Du kannst mit **!open** und" 
                            f"**!close** den Status dieser Gruppe setzen. Bedenke aber bitte, dass die Discord" 
                            f"API die möglichen Namensänderungen stark limitiert. Daher ist nur ein Statuswechsel" 
                            f"alle **5 Minuten** möglich.")

        self.groups["groups"][str(channel.id)] = {"owner_id": requested_channel_config["owner_id"]}

        await self.remove_group_request(message)
        if not direct:
            await message.delete()

        await self.save_groups()
        await self.update_statusmessage()

    async def remove_group_request(self, message):
        del self.groups["requested"][str(message.id)]
        await self.save_groups()

    async def remove_group(self, channel):
        del self.groups["groups"][str(channel.id)]
        await self.save_groups()

    def channel_to_channel_config(self, channel):
        cid = str(channel.id)
        result = re.match(r"([0-9]{4,6})-(.*)-([a-z0-9]+)$", channel.name[1:])
        is_open = channel.name[0] == LG_OPEN_SYMBOL
        course, name, semester = result.group(1, 2, 3)

        channel_config = {"course": course, "name": name, "category": channel.category_id, "semester": semester,
                          "is_open": is_open, "channel_id": cid}
        if self.groups["groups"].get(cid):
            channel_config.update(self.groups["groups"].get(cid))
        return channel_config

    async def update_channels(self):
        self.channels = {}
        for is_open in [True, False]:
            category = await self.category_of_channel(is_open)

            for channel in category.text_channels:
                channel_config = self.channel_to_channel_config(channel)
                #if not await self.is_channel_config_valid(ctx, channel_config):
                #    await utils.send_dm(ctx.author, f"Info: Channelname hat falsches Format: {channel.name}")

                self.channels[str(channel.id)] = channel_config
        print([self.channels])

    @commands.group(name="learninggroup", aliases=["lg", "lerngruppe"], pass_context=True)
    async def cmd_learninggroup(self, ctx):
        pass
        #if not ctx.invoked_subcommand:
        #    await self.cmd_module_info(ctx)

    @help(
        command_group="learninggroup",
        category="learninggroups",
        brief="Erstellt aus den Lerngruppen-Kanälen eine Datendatei. ",
        description=(
                "Initialisiert alle Gruppen in den Kategorien für offene und geschlossene Lerngruppen "
                "und baut die Verwaltungsdaten dazu auf. "
                "Die Lerngruppen-Kanal-Namen müssen hierfür zuvor ins Format "
                "#{symbol}{kursnummer}-{name}-{semester} gebracht werden. "
                "Als Owner wird der ausführende Account für alle Lerngruppen gesetzt. "
                "Wenn die Verwaltungsdatenbank nicht leer ist, wird das Kommando nicht ausgeführt. "
        ),
        mod=True
    )

    @cmd_learninggroup.command(name="update")
    @commands.check(utils.is_mod)
    async def cmd_update(self, ctx):
        await self.update_channels()
        await self.update_statusmessage()


    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg header <coursenumber> <name...>",
        brief="Fügt einen Kurs als neue Überschrift in Botys Lerngruppen-Liste (Kanal #lerngruppen) hinzu. Darf Leerzeichen enthalten, Anführungszeichen sind nicht erforderlich.",
        example="!lg header 1141 Mathematische Grundlagen",
        parameters={
            "coursenumber": "Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
            "name...": "Ein frei wählbarer Text (darf Leerzeichen enthalten).",
        },
        description="Kann auch zum Bearbeiten einer Überschrift genutzt werden. Bei bereits existierender Kursnummer wird die Überschrift abgeändert",
        mod=True
    )
    @cmd_learninggroup.command(name="header")
    @commands.check(utils.is_mod)
    async def cmd_add_course(self, ctx, arg_course, *arg_name):
        if not re.match(r"[0-9]+", arg_course):
            await ctx.channel.send(
                f"Fehler! Die Kursnummer muss numerisch sein. Gib `!help add-course` für Details ein.")
            return

        self.header[arg_course] = f"{arg_course} - {' '.join(arg_name)}"
        self.save_header()
        await self.update_statusmessage()

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg add <coursenumber> <name> <semester> <status> <@usermention>",
        example="!lg add 1142 mathegenies sose22 closed @someuser",
        brief="Fügt einen Lerngruppen-Kanal hinzu. Der Name darf keine Leerzeichen enthalten.",
        parameters={
            "coursenumber": "Nummer des Kurses wie von der Fernuni angegeben (ohne führende Nullen z. B. 1142).",
            "name": "Ein frei wählbarer Text ohne Leerzeichen. Bindestriche sind zulässig.",
            "semester": "Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der zweistelligen Jahreszahl (z. B. sose22).",
            "status": "Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed).",
            "@usermention": "Der so erwähnte Benutzer wird als Besitzer für die Lerngruppe gesetzt."
        },
        mod=True
    )
    @cmd_learninggroup.command(name="add")
    @commands.check(utils.is_mod)
    async def cmd_add_group(self, ctx, arg_course, arg_name, arg_semester, arg_open, arg_owner: discord.Member):
        is_open = self.arg_open_to_bool(arg_open)
        channel_config = {"owner_id": arg_owner.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "is_open": is_open}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name):
            return

        self.groups["requested"][str(ctx.message.id)] = channel_config
        await self.save_groups()
        await self.add_requested_group_channel(ctx.message, direct=True)

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg request <coursenumber> <name> <semester> <status>",
        brief="Stellt eine Anfrage für einen neuen Lerngruppen-Kanal.",
        example="!lg request 1142 mathegenies sose22 closed",
        description=("Moderatorinnen können diese Anfrage bestätigen, dann wird die Gruppe eingerichtet. "
                     "Der Besitzer der Gruppe ist der Benutzer der die Anfrage eingestellt hat."),
        parameters={
            "coursenumber": "Nummer des Kurses, wie von der FernUni angegeben (ohne führende Nullen z. B. 1142).",
            "name": "Ein frei wählbarer Text ohne Leerzeichen.",
            "semester": "Das Semester, für welches diese Lerngruppe erstellt werden soll. sose oder wise gefolgt von der zweistelligen Jahrenszahl (z. B. sose22).",
            "status": "Gibt an ob die Lerngruppe für weitere Lernwillige geöffnet ist (open) oder nicht (closed)."
        }
    )
    @cmd_learninggroup.command(name="request", aliases=["r", "req"])
    async def cmd_request_group(self, ctx, arg_course, arg_name, arg_semester, arg_open):
        is_open = self.arg_open_to_bool(arg_open)
        channel_config = {"owner_id": ctx.author.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "is_open": is_open}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name):
            return

        channel_name = self.full_channel_name(channel_config)
        embed = discord.Embed(title="Lerngruppenanfrage!",
                              description=f"<@!{ctx.author.id}> möchte gerne die Lerngruppe **#{channel_name}** eröffnen",
                              color=19607)

        channel_request = await self.bot.fetch_channel(int(self.channel_request))
        message = await channel_request.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")

        self.groups["requested"][str(message.id)] = channel_config
        await self.save_groups()

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg open",
        brief="Öffnet den Lerngruppen-Kanal wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Verschiebt den Lerngruppen-Kanal in die Kategorie für offene Kanäle und ändert das Icon. "
                     "Diese Aktion kann nur vom Besitzer der Lerngruppe ausgeführt werden. ")
    )
    @cmd_learninggroup.command(name="open")
    async def cmd_open(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, is_open=True)

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg close",
        brief="Schließt den Lerngruppen-Kanal wenn du die Besitzerin bist. ",
        description=("Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. "
                     "Verschiebt den Lerngruppen-Kanal in die Kategorie für geschlossene Kanäle und ändert das Icon. "
                     "Diese Aktion kann nur vom Besitzer der Lerngruppe ausgeführt werden. ")
    )
    @cmd_learninggroup.command(name="close")
    async def cmd_close(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, is_open=False)

    @help(
        command_group="learninggroup",
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
    @cmd_learninggroup.command(name="rename")
    @commands.check(utils.is_mod)
    async def cmd_rename(self, ctx, arg_name):
        await self.set_channel_name(ctx.channel, arg_name)

    @help(
        command_group="learninggroup",
        syntax="!lg archive",
        category="learninggroups",
        brief="Archiviert den Lerngruppen-Kanal",
        description="Verschiebt den Lerngruppen-Kanal, in welchem dieses Kommando ausgeführt wird, ins Archiv.",
        mod=True
    )
    @cmd_learninggroup.command(name="archive", aliases=["archiv"])
    @commands.check(utils.is_mod)
    async def cmd_archive(self, ctx):
        await self.archive(ctx.channel)

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg owner <@usermention>",
        example="!owner @someuser",
        brief="Setzt die Besitzerin eines Lerngruppen-Kanals",
        description="Muss im betreffenden Lerngruppen-Kanal ausgeführt werden. ",
        parameters={
            "@usermention": "Der neue Besitzer der Lerngruppe."
        },
        mod=True
    )
    @cmd_learninggroup.command(name="owner")
    @commands.check(utils.is_mod)
    async def cmd_owner(self, ctx, arg_owner: discord.Member = None):
        group_config = self.groups["groups"].get(str(ctx.channel.id))

        if not arg_owner:
            owner_id = group_config.get("owner_id")
            if owner_id:
                user = await self.bot.fetch_user(owner_id)
                await ctx.channel.send(f"Besitzer: @{user.name}")

        elif group_config:
            group_config["owner_id"] = arg_owner.id
            await self.save_groups()
            await ctx.channel.send(f"Glückwunsch {arg_owner.mention}! Du bist jetzt die Besitzerin dieser Lerngruppe.")



    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg addmember <@usermention>",
        example="!lg addmember @someuser",
        brief="Fügt einen Benutzer zu einer Lerngruppe hinzu.",
        parameters={
            "@usermention": "Der so erwähnte Benutzer wird zur Lerngruppe hinzugefügt."
        },
        mod=True
    )
    @cmd_learninggroup.command(name="addmember", aliases=["addm", "am"])
    async def cmd_add_member(self, ctx, arg_member: discord.Member):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.add_member(ctx.channel, arg_member)

    async def add_member(self, channel:discord.TextChannel, arg_member: discord.Member):
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
        group_config["users"] = users

        await self.save_groups()


    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg removemember <@usermention>",
        example="!lg removemember @someuser",
        brief="Entfernt einen Benutzer aus einer Lerngruppe.",
        parameters={
            "@usermention": "Der so erwähnte Benutzer wird aus der Lerngruppe entfernt."
        },
        mod=True
    )
    @cmd_learninggroup.command(name="removemember", aliases=["remm", "rm"])
    async def cmd_remove_member(self, ctx, arg_member: discord.Member):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            group_config = self.groups["groups"].get(str(ctx.channel.id))
            if not group_config:
                await ctx.channel.send("Das ist kein Lerngruppenkanal.")
                return

            users = group_config.get("users")
            if not users:
                return
            mid = str(arg_member.id)
            users.pop(mid, None)

            await self.save_groups()

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg id",
        brief="Zeigt die ID für deine Lerngruppe an.",
    )
    @cmd_learninggroup.command(name="id")
    async def cmd_id(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            group_config = self.groups["groups"].get(str(ctx.channel.id))
            if not group_config:
                await ctx.channel.send("Das ist kein Lerngruppenkanal.")
                return

        await utils.send_dm(ctx.author, "Die ID deiner Lerngruppe lautet: " + str(ctx.channel.id))

    @help(
        command_group="learninggroup",
        category="learninggroups",
        syntax="!lg join <lg-id>",
        brief="Fragt bei einer Lerngruppe um Aufnahme.",
        parameters={
            "id": "Die ID zur Lerngruppe."
        }
    )
    @cmd_learninggroup.command(name="join")
    async def cmd_join(self, ctx, arg_id):
        group_config = self.groups["groups"].get(str(arg_id))
        if not group_config:
            await ctx.channel.send("Das ist keine gültiger Lerngruppenkanal.")
            return

        owner = self.bot.get_user(group_config["owner_id"])
        channel = await self.bot.fetch_channel(int(arg_id))

        #channel_name = self.full_channel_name(channel_config)
        embed = discord.Embed(title="Jemand möchte deiner Lerngruppe beitreten!",
                              description=f"<@!{ctx.author.id}> möchte gerne der Lerngruppe **#{channel.name}** beitreten.",
                              color=19607)

        message = await channel.send(f"Anfrage von <@!{ctx.author.id}>", embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if str(channel.id) == str(self.channel_request):
            request = self.groups["requested"].get(str(message.id))
            if payload.emoji.name in ["👍"] and self.is_group_request_message(message) and self.is_mod(payload.member):
                await self.add_requested_group_channel(message, direct=False)

            if payload.emoji.name in ["🗑️"] and self.is_group_request_message(message) and (
                    self.is_request_owner(request, payload.member) or self.is_mod(payload.member)):
                await self.remove_group_request(message)
                await message.delete()
        else:
            group_config = self.groups["groups"].get(str(channel.id))
            if not group_config:
                return

            if payload.emoji.name in ["👍"] and self.is_group_owner(channel, payload.member):
                if message.mentions and len(message.mentions) == 1:
                    await self.add_member(channel, message.mentions[0])
                    overwrites = await self.overwrites(channel)
                    await channel.edit(overwrites=overwrites)
                else:
                    await channel.send(f"Leider ist ein Fehler aufgetreten.")

                await message.delete()

            if payload.emoji.name in ["🗑️"] and self.is_group_owner(channel, payload.member):
                await message.delete()

    async def overwrites(self, channel):
        channel = await self.bot.fetch_channel(str(channel.id))
        group_config = self.groups["groups"].get(str(channel.id))
        guild = await self.bot.fetch_guild(int(self.guild_id))

        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}

        users = group_config.get("users")
        if not users:
            return

        for userid in users.keys():
            user = await self.bot.fetch_user(userid)
            overwrites[user] = discord.PermissionOverwrite(read_messages=True)

        return overwrites

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
>>>>>>> d853e28... parse channel attributes directly from discord to prevent redundant data.
