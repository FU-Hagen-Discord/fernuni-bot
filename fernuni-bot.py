import json
import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

from appointments_cog import AppointmentsCog
from poll import Poll
from text_commands_cog import TextCommandsCog

# .env file is necessary in the same directory, that contains several strings.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
OWNER = int(os.getenv('DISCORD_OWNER'))
ROLES_FILE = os.getenv('DISCORD_ROLES_FILE')
HELP_FILE = os.getenv('DISCORD_HELP_FILE')
TOPS_FILE = os.getenv('DISCORD_TOPS_FILE')
APPOINTMENTS_FILE = os.getenv("DISCORD_APPOINTMENTS_FILE")
TEXT_COMMANDS_FILE = os.getenv("DISCORD_TEXT_COMMANDS_FILE")
DATE_TIME_FORMAT = os.getenv("DISCORD_DATE_TIME_FORMAT")
CATEGORY_LERNGRUPPEN = os.getenv("DISCORD_CATEGORY_LERNGRUPPEN")

PIN_EMOJI = "📌"
bot = commands.Bot(command_prefix='!', help_command=None, activity=discord.Game(ACTIVITY), owner_id=OWNER)
appointments_cog = AppointmentsCog(bot, DATE_TIME_FORMAT, APPOINTMENTS_FILE)
text_commands_cog = TextCommandsCog(bot, TEXT_COMMANDS_FILE)
bot.add_cog(appointments_cog)
bot.add_cog(text_commands_cog)
assignable_roles = {}
tops = {}


def get_guild():
    """ Returns an guild object, that matches the id specified in GUILD.
    This guild is the FU Hagen Informatik/Mathematik guild."""

    for guild in bot.guilds:
        if guild.id == GUILD:
            return guild

    return None


def get_key(role):
    """ Get the key for a given role. This role is used for adding or removing a role from a user. """

    for key, role_name in assignable_roles.items():
        if role_name == role.name:
            return key


def get_member(user):
    """ Get Member from passed user """

    if type(user) is discord.Member:
        return user
    elif type(user) is discord.User:
        guild = get_guild()
        if guild is not None:
            return guild.get_member(user.id)
    return None


def get_roles(user=None):
    """ Get all roles assigned to a member, or all roles available on the discord server
    (in both cases only roles are returned, that are defined in roles.json). """
    roles_list = []
    roles_dict = {}

    if user is not None:
        member = get_member(user)
        if member is not None:
            roles_list = member.roles
    else:
        guild = get_guild()
        if guild is not None:
            roles_list = guild.roles

    for role in roles_list:
        role_key = get_key(role)
        if role_key is not None:
            roles_dict[role_key] = role
    return roles_dict


def get_reaction(reactions):
    """ Returns the reaction, that is equal to the specified PIN_EMOJI,
    or if that reaction does not exist in list of reactions, None will be returned"""

    for reaction in reactions:
        if reaction.emoji == PIN_EMOJI:
            return reaction
    return None


async def send_dm(user, message, embed=None):
    """ Send DM to a user/member """

    if type(user) is discord.User or type(user) is discord.Member:
        if user.dm_channel is None:
            await user.create_dm()

        await user.dm_channel.send(message, embed=embed)


@bot.command(name="help")
async def cmd_help(ctx):
    """ Send help message as DM """

    help_file = open(HELP_FILE, mode='r')
    help_dict = json.load(help_file)
    embed = discord.Embed.from_dict(help_dict)
    await send_dm(ctx.author, "", embed=embed)


def get_role_embed(title, roles):
    """ Returns an embed that represents all the roles that are passed to this function """

    embed = discord.Embed(title=title,
                          description="Bei jeder Rolle siehst du oben in Fett den Key der Rolle und "
                                      "darunter den Namen der Rolle",
                          color=19607)
    embed.add_field(name="\u200B", value="\u200B", inline=False)

    for key, role in roles.items():
        embed.add_field(name=key, value=role.name, inline=False)

    return embed


@bot.command(name="all-roles")
async def cmd_all_roles(message):
    """ Send all available roles that can be assigned to a member by this bot as DM """

    roles = get_roles()
    embed = get_role_embed("Alle verfügbaren Rollen", roles)
    await send_dm(message.author, "", embed=embed)


@bot.command(name="my-roles")
async def cmd_my_roles(message):
    """ Send the roles assigned to a member as DM. """

    roles = get_roles(message.author)
    embed = get_role_embed("Dir zugewiesene Rollen", roles)
    await send_dm(message.author, "", embed=embed)


@bot.command(name="add-roles")
async def cmd_add_roles(ctx, *args):
    """ Add yourself one or more roles """

    if len(args) > 0:
        await modify_roles(ctx, True, args)


@bot.command(name="remove-roles")
async def cmd_remove_roles(ctx, *args):
    """ Remove roles assigned to you """

    if len(args):
        await modify_roles(ctx, False, args)


@bot.command(name="add-role")
@commands.is_owner()
async def cmd_add_role(ctx, key, role):
    """ Add a Role to be assignable (Admin-Command only) """

    assignable_roles[key] = role
    roles_file = open(ROLES_FILE, mode='w')
    json.dump(assignable_roles, roles_file)

    if key in assignable_roles:
        await send_dm(ctx.author, f"Rolle {role} wurde hinzugefügt")
    else:
        await send_dm(ctx.author, f"Fehler beim Hinzufügen der Rolle {role}")


@bot.command(name="poll")
async def cmd_poll(ctx, question, *answers):
    """ Create poll """

    await Poll(bot, question, answers, ctx.author.id).send_poll(ctx)


@bot.command(name="add-top")
async def cmd_add_top(ctx, top):
    """ Add TOP to a channel """

    channel = ctx.channel

    if str(channel.id) not in tops:
        tops[str(channel.id)] = []

    channel_tops = tops.get(str(channel.id))
    channel_tops.append(top)

    tops_file = open(TOPS_FILE, mode='w')
    json.dump(tops, tops_file)


@bot.command(name="remove-top")
async def cmd_remove_top(ctx, top):
    """ Remove TOP from a channel """
    channel = ctx.channel

    if not re.match(r'^-?\d+$', top):
        await ctx.send("Fehler! Der übergebene Parameter muss eine Zahl sein")
    else:
        if str(channel.id) in tops:
            channel_tops = tops.get(str(channel.id))

            if 0 < int(top) <= len(channel_tops):
                del channel_tops[int(top) - 1]

            if len(channel_tops) == 0:
                tops.pop(str(channel.id))

            tops_file = open(TOPS_FILE, mode='w')
            json.dump(tops, tops_file)


@bot.command(name="clear-tops")
async def cmd_clear_tops(ctx):
    """ Clear all TOPs from a channel """

    channel = ctx.channel

    if str(channel.id) in tops:
        tops.pop(str(channel.id))
        tops_file = open(TOPS_FILE, mode='w')
        json.dump(tops, tops_file)


@bot.command(name="tops")
async def cmd_tops(ctx):
    """ Get all TOPs from a channel """

    channel = ctx.channel

    embed = discord.Embed(title="Tagesordnungspunkte",
                          color=19607)
    embed.add_field(name="\u200B", value="\u200B", inline=False)

    if str(channel.id) in tops:
        channel_tops = tops.get(str(channel.id))

        for i in range(0, len(channel_tops)):
            embed.add_field(name=f"TOP {i + 1}", value=channel_tops[i], inline=False)
    else:
        embed.add_field(name="Keine Tagesordnungspunkte vorhanden", value="\u200B", inline=False)

    await ctx.send(embed=embed)


def load_roles():
    """ Loads all assignable roles from ROLES_FILE """
    global assignable_roles
    roles_file = open(ROLES_FILE, mode='r')
    assignable_roles = json.load(roles_file)


def load_tops():
    """ Loads all TOPs from TOPS_FILE """
    global tops
    tops_file = open(TOPS_FILE, mode='r')
    tops = json.load(tops_file)


async def modify_roles(ctx, add, args):
    """ Add or remove roles assigned to a member. Multiple roles can be added with one command, or removed. """

    guild = get_guild()

    if guild is not None:
        member = get_member(ctx.author)

        roles = get_roles()
        for key in args:
            if key in roles:
                role = roles[key]
                if add:
                    try:
                        await member.add_roles(role)
                        await send_dm(ctx.author, f'Dir wurde die Rolle {role.name} hinzugefügt')
                    except Exception:
                        await send_dm(ctx.author, f'Fehler bei der Zuweisung der Rolle {role.name}')
                else:
                    try:
                        await member.remove_roles(role)
                        await send_dm(ctx.author, f'Dir wurde die Rolle {role.name} entfernt')
                    except Exception:
                        await send_dm(ctx.author, f'Fehler bei der Entfernung der Rolle {role.name}')


@bot.command(name="stats")
async def cmd_stats(message):
    """ Sends stats in Chat. """

    guild = get_guild()
    members = await guild.fetch_members().flatten()
    roles = get_roles()
    answer = f''
    embed = discord.Embed(title="Statistiken",
                          description=f'Wir haben aktuell {len(members)} Mitglieder auf diesem Server, verteilt auf folgende Rollen:')
    for key, role in roles.items():
        role_members = role.members
        if len(role_members) > 0 and not role.name.startswith("Farbe"):
            embed.add_field(name=role.name, value=f'{len(role_members)} Mitglieder', inline=False)

    no_role = 0
    for member in members:
        # ToDo Search for study roles only!
        if len(member.roles) == 1:
            no_role += 1

    embed.add_field(name="\u200B", value="\u200b", inline=False)
    embed.add_field(name="Mitglieder ohne Rolle", value=str(no_role), inline=False)

    await message.channel.send(answer, embed=embed)


async def pin_message(message):
    """ Pin the given message, if it is not already pinned """

    if not message.pinned:
        await message.pin()
        await message.channel.send(f'Folgende Nachricht wurde gerade angepinnt: {message.jump_url}')


async def unpin_message(message):
    """ Unpin the given message, if it is pinned, and it has no pin reaction remaining. """

    if message.pinned:
        reaction = get_reaction(message.reactions)
        if reaction is None:
            await message.unpin()
            await message.channel.send(f'Folgende Nachricht wurde gerade losgelöst: {message.jump_url}')


@bot.event
async def on_ready():
    print("Client started!")
    load_roles()
    load_tops()


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await pin_message(message)
    elif payload.emoji.name in ["🗑️", "🛑"]:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if len(message.embeds) > 0 and message.embeds[0].title == "Umfrage":
            poll = Poll(bot, message=message)
            if str(payload.user_id) == poll.author:
                if payload.emoji.name == "🗑️":
                    await poll.delete_poll()
                else:
                    await poll.close_poll()
        elif payload.emoji.name == "🗑️" and len(message.embeds) > 0 and \
                message.embeds[0].title == "Neuer Termin hinzugefügt!":
            await appointments_cog.handle_reactions(payload)
    elif payload.emoji.name in ["👍"]:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if len(message.embeds) > 0 and message.embeds[0].title == "Neuer Motivations Text":
            await text_commands_cog.motivation_approved(message)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await unpin_message(message)


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel and after.channel and "Lerngruppen-Voice" in after.channel.name:
        category = await bot.fetch_channel(CATEGORY_LERNGRUPPEN)
        voice_channels = category.voice_channels

        for voice_channel in voice_channels:
            if len(voice_channel.members) == 0:
                return

        await category.create_voice_channel(f"Lerngruppen-Voice-{len(voice_channels) + 1}")


bot.run(TOKEN)
