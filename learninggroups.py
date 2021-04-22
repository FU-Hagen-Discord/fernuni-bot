import json
import os
import time
import re
import discord
import utils
from discord.ext import commands

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

  Kommandos für Moderatoren:
    !init-groups 
      Initalisiert alle Gruppen in den Kategorien für offene und geschlossele Lerngruppen und baut die Verwaltungsdaten dazu auf.
      Die Lerngruppen-Kanal-Namen müssen hierfür zuvor ins Format #{symbol}{kursnummer}-{name}-{semester} gebracht werden.
      Als Owner wird der ausführende Account für alle Lerngruppen gesetzt. 
      Wenn die Verwaltungsdatenbank nicht leer ist, wird das Kommando nicht ausgeführt.
    !owner <@usermention> (z.B. !owner @ffaadd)
      Muss im betreffenden Lerngruppenkanal ausgeführt werden.
      Setzt den Besitzer für diesen Kanal auf den User der in der Mention erwähnt wird
    !show-owner
      Muss im betreffenden Lerngruppenkanal ausgeführt werden.
      Zeigt den momentanen Besitzer dieses Kanals an.
    !add-course <coursenumber> <*name> (z.B. !add-course 1142 Mathematische Grundlagen)
      Fügt einen Kurs zur Kursnamen-Datei hinzu. Der Name kann Leerzeichen enthalten
    !add-group <coursenumber> <name> <semester> <open|closed> <@owner> (z.B. !add-group 1142 matheprofis sose22 open @ffaadd)
      Fügt einen Lerngruppenkanal hinzu. Der Name darf KEINE Leerzeichen enthalten.
    !rename <name> (z.B. !rename matheluschen)
      Ändert den Namen des Lerngruppenkanals in dem das Komando ausgeführt wird. 
      Aus #1142-matheprofis-sose22 wird nach dem Aufruf des Beispiels #1142-matheluschen-sose22.

  Kommandos für Besitzer:
    !open
      Muss im betreffenden Lerngruppenkanal ausgeführt werden.
      Verschiebt den Lerngruppenkanal in die Kategorie für offene Kanäle und ändert das Icon
    !close
      Muss im betreffenden Lerngruppenkanal ausgeführt werden.
      Verschiebt den Lerngruppenkanal in die Kategorie für geschlossene Kanäle und ändert das Icon

  Kommandos für Benutzer:
    !request-group <coursenumber> <name> <semester> <open|closed> (z.B. !request-group 1142 matheprofis sose22 open)
      Stellt eine Anfrage für einen Lerngruppen-Kanal. Moderatoren können diese bestätigen (dann wird die Gruppe 
      wie bei !add-group eingerichtet) oder verwerfen. Der Besitzer der Gruppe ist der Benutzer der die Anfrage eingestellt hat.
"""


class LearningGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rename_ratelimit = 305  # ratelimit 2 in 10 minutes (305 * 2 = 610 = 10 minutes and 10 seconds)
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
        self.cmd_syntax = {
            "add-group": "`!add-group <coursenumber> <name> <soseYY|wiseYY)> <open|closed> <@usermention>`\n"
                         "`!add-group 1142 mathegenies sose22 clsoed @someuser`",
            "add-course": "`!add-course <coursenumber> <*name>`\n"
                          "`!add-course 1141 Mathematische Grundlagen`",
            "request-group": "`!request-group <coursenumber> <name> <soseYY|wiseYY> <open|closed>`\n"
                             "`!request-group 1142 mathegenies sose22 closed`",
            "owner": "`!owner <@usermention>`\n"
                     "`!owner @someuser`\n"
        }

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
        if arg_open in ["offen", "open"]: return True
        if arg_open in ["geschlossen", "closed", "close"]: return False
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
            if command: await ctx.channel.send(
                f"Fehler! Bitte gib an ob die Gruppe **offen** (**open**) oder **geschlossen** (**closed**) ist\n{self.cmd_syntax[command]}")
            return False
        if not re.match(r"^[0-9]+$", channel_config['course']):
            if command: await ctx.channel.send(
                f"Fehler! Die Kursnummer muss numerisch sein\n{self.cmd_syntax[command]}")
            return False
        if not re.match(r"^(sose|wise)[0-9]{2}$", channel_config['semester']):
            if command: await ctx.channel.send(
                f"Fehler! Das Semester muss mit **sose** oder **wise** angegeben werden gefolgt von der **zweistelligen Jahreszahl**\n{self.cmd_syntax[command]}")
            return False
        return True

    async def check_rename_rate_limit(self, channel_config):
        if channel_config.get("last_rename") is None: return False
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
        info_message_id = self.groups.get("messageid")

        msg = f"**Lerngruppen**\n\n"
        sorted_groups = sorted(self.groups["groups"].values(), key=lambda group: f"{group['course']}-{group['name']}")
        open_groups = [group for group in sorted_groups if group['is_open']]
        courseheader = None
        for group in open_groups:
            if group['course'] != courseheader:
                header = self.header.get(group['course'])
                if header:
                    msg += f"**{header}**\n"
                else:
                    msg += f"**{group['course']} - -------------------------------------**\n"
                courseheader = group['course']

            groupchannel = await self.bot.fetch_channel(int(group['channel_id']))
            msg += f"    {groupchannel.mention}\n"

        channel = await self.bot.fetch_channel(int(self.channel_info))

        if (info_message_id == None):
            message = await channel.send(msg)
        else:
            message = await channel.fetch_message(int(info_message_id))
            await message.edit(content=msg)
        self.groups["messageid"] = message.id
        self.save_groups()

    async def archive(self, channel):
        category = await self.bot.fetch_channel(self.category_archive)
        await self.move_channel(channel, category)
        await channel.edit(name=f"archiv-${channel.name[1:]}")
        self.remove_group(channel)

    async def set_channel_state(self, channel, is_open):
        channel_config = self.groups["groups"][str(channel.id)]
        if await self.check_rename_rate_limit(channel_config): return  # prevent api requests when ratelimited

        was_open = channel_config["is_open"]
        if (was_open == is_open): return  # prevent api requests when nothing changed

        channel_config["is_open"] = is_open
        channel_config["last_rename"] = int(time.time())

        await channel.edit(name=self.full_channel_name(channel_config))
        category = await self.category_of_channel(is_open)
        await self.move_channel(channel, category)
        await self.update_groupinfo()
        self.save_groups()

    async def set_channel_name(self, channel, name):
        channel_config = self.groups["groups"][str(channel.id)]

        if await self.check_rename_rate_limit(channel_config): return  # prevent api requests when ratelimited

        channel_config["name"] = name
        channel_config["last_rename"] = int(time.time())

        await channel.edit(name=self.full_channel_name(channel_config))
        await self.update_groupinfo()
        self.save_groups()

    async def move_channel(self, channel, category):
        for sortchannel in category.text_channels:
            if sortchannel.name[1:] > channel.name[1:]:
                await channel.move(category=category, before=sortchannel)
                return
        await channel.move(category=category, end=True)

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
                result = re.match(r"([0-9]{4,6})-(.*)-([a-z0-9]+)$", channel.name[1:])
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

    @commands.command(name="add-course")
    @commands.check(utils.is_mod)
    async def cmd_add_course(self, ctx, arg_course, *arg_name):
        if not re.match(r"[0-9]+", arg_course):
            await ctx.channel.send(f"Fehler! Die Kursnummer muss numerisch sein\n{self.cmd_syntax['add-course']}")
            return

        self.header[arg_course] = f"{arg_course} - {' '.join(arg_name)}"
        self.save_header()
        await self.update_groupinfo()

    @commands.command(name="add-group")
    @commands.check(utils.is_mod)
    async def cmd_add_group(self, ctx, arg_course, arg_name, arg_semester, arg_open, arg_owner: discord.Member):
        is_open = self.arg_open_to_bool(arg_open)
        channel_config = {"owner_id": arg_owner.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "is_open": is_open}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name): return

        self.groups["requested"][str(ctx.message.id)] = channel_config
        self.save_groups()
        await self.add_requested_group_channel(ctx.message, direct=True)

    @commands.command(name="request-group")
    async def cmd_request_group(self, ctx, arg_course, arg_name, arg_semester, arg_open):
        is_open = self.arg_open_to_bool(arg_open)
        channel_config = {"owner_id": ctx.author.id, "course": arg_course, "name": arg_name, "semester": arg_semester,
                          "is_open": is_open}

        if not await self.is_channel_config_valid(ctx, channel_config, ctx.command.name): return

        channel_name = self.full_channel_name(channel_config)
        embed = discord.Embed(title="Lerngruppenanfrage!",
                              description=f"<@!{ctx.author.id}> möchte gerne die Lerngruppe **#{channel_name}** eröffnen",
                              color=19607)

        channel_request = await self.bot.fetch_channel(int(self.channel_request))
        message = await channel_request.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("🗑️")

        self.groups["requested"][str(message.id)] = channel_config
        self.save_groups()

    @commands.command(name="open")
    async def cmd_open(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, is_open=True)

    @commands.command(name="close")
    async def cmd_close(self, ctx):
        if self.is_group_owner(ctx.channel, ctx.author) or utils.is_mod(ctx):
            await self.set_channel_state(ctx.channel, is_open=False)

    @commands.command(name="rename")
    @commands.check(utils.is_mod)
    async def cmd_rename(self, ctx, arg_name):
        await self.set_channel_name(ctx.channel, arg_name)

    @commands.command(name="archive")
    @commands.check(utils.is_mod)
    async def cmd_archive(self, ctx):
        await self.archive(ctx.channel)

    @commands.command(name="owner")
    @commands.check(utils.is_mod)
    async def cmd_owner(self, ctx, arg_owner: discord.Member):
        channel_config = self.groups["groups"].get(str(ctx.channel.id))
        if channel_config:
            channel_config["owner_id"] = arg_owner.id
            self.save_groups()
            await ctx.channel.send(f"Glückwunsch {arg_owner.mention}! Du bist jetzt die Besitzerin dieser Lerngruppe.")

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
        if payload.user_id == self.bot.user.id: return

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
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.channel.send(f"Fehler! Du hast ein Argument vergessen.\n{self.cmd_syntax[ctx.command.name]}")
        else:
            raise error
