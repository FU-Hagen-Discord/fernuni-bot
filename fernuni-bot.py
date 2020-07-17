import json
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

# .env file is necessary in the same directory, that contains several strings.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
OWNER = int(os.getenv('DISCORD_OWNER'))
ROLES_FILE = os.getenv('DISCORD_ROLES_FILE')
HELP_FILE = os.getenv('DISCORD_HELP_FILE')

PIN_EMOJI = "📌"
bot = commands.Bot(command_prefix='!', help_command=None, activity=discord.Game(ACTIVITY), owner_id=OWNER)
assignable_roles = {}


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


def get_guild_roles():
    """ Get all roles that are available at the guild. """

    guild = get_guild()
    if guild is not None:
        roles = {}
        for role in guild.roles:
            role_key = get_key(role)
            if role_key is not None:
                roles[role_key] = role
        return roles
    return None


def get_member(user):
    if type(user) is discord.Member:
        return user
    elif type(user) is discord.User:
        guild = get_guild()
        if guild is not None:
            return guild.get_member(user.id)
    return None


def get_members_roles(user):
    """ Get all roles assigned to a member. """

    member = get_member(user)
    if member is not None:
        return member.roles
    return None


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
async def fu_help(ctx):
    """ Send help message as DM """

    help_file = open(HELP_FILE, mode='r')
    help_dict = json.load(help_file)
    embed = discord.Embed.from_dict(help_dict)
    await send_dm(ctx.author, "", embed=embed)


@bot.command(name="all-roles")
async def fu_all_roles(message):
    """ Send all available roles that can be assigned to a member by this bot as DM """

    roles = get_guild_roles()
    answer = "Verfügbare Rollen: \n"
    for key, role in roles.items():
        answer += f'[{key}] {role.name}\n'

    await send_dm(message.author, answer)


@bot.command(name="my-roles")
async def fu_my_roles(message):
    """ Send the roles assigned to a member as DM. """

    my_roles = get_members_roles(message.author)
    answer = "Dir zugewiesene Rollen:\n"

    if my_roles is not None:
        for role in my_roles:
            key = get_key(role)
            if key is not None:
                answer += f'[{key}] {role.name} \n'

    await send_dm(message.author, answer)


@bot.command(name="add-roles")
async def fu_add_roles(ctx, *args):
    if len(args) > 0:
        await modify_roles(ctx, True, args)


@bot.command(name="remove-roles")
async def fu_remove_roles(ctx, *args):
    if len(args):
        await modify_roles(ctx, False, args)


@bot.command(name="add-role")
@commands.is_owner()
async def fu_add_role(ctx, key, role):
    assignable_roles[key] = role
    roles_file = open(ROLES_FILE, mode='w')
    json.dump(assignable_roles, roles_file)

    if key in assignable_roles:
        await send_dm(ctx.author, f"Rolle {role} wurde hinzugefügt")
    else:
        await send_dm(ctx.author, f"Fehler beim Hinzufügen der Rolle {role}")


def fu_load_roles():
    global assignable_roles
    roles_file = open(ROLES_FILE, mode='r')
    assignable_roles = json.load(roles_file)


async def modify_roles(ctx, add, args):
    """ Add or remove roles assigned to a member. Multiple roles can be added with one command, or removed. """

    guild = get_guild()

    if guild is not None:
        member = get_member(ctx.author)

        roles = get_guild_roles()
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


@bot.command(name="link")
async def fu_link(message):
    """ Sends link to invite others to Discord server in Chat. """

    await message.channel.send('Benutze bitte folgenden Link, um andere Studierende auf unseren Discord einzuladen: '
                               'http://fernuni-discord.dnns01.de')


@bot.command(name="stats")
async def fu_stats(message):
    """ Sends stats in Chat. """

    guild = get_guild()
    members = await guild.fetch_members().flatten()
    roles = get_guild_roles()
    answer = f'Wir haben aktuell {len(members)} Mitglieder auf diesem Server.'
    answer += f'\n\nVerteilt auf Rollen: '

    for key, role in roles.items():
        role_members = role.members
        if len(role_members) > 0 and not role.name.startswith("Farbe"):
            answer += f'\n{role.name}: {len(role_members)} Mitglieder'

    no_role = 0
    for member in members:
        if len(member.roles) == 1:
            no_role += 1

    answer += f'\n\n{no_role} Mitglieder ohne Rolle'

    await message.channel.send(answer)


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
    fu_load_roles()


@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await pin_message(message)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await unpin_message(message)


bot.run(TOKEN)
