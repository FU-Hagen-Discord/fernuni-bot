import json
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from poll import Poll

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


def get_member(user):
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
    if len(args) > 0:
        await modify_roles(ctx, True, args)


@bot.command(name="remove-roles")
async def cmd_remove_roles(ctx, *args):
    if len(args):
        await modify_roles(ctx, False, args)


@bot.command(name="add-role")
@commands.is_owner()
async def cmd_add_role(ctx, key, role):
    assignable_roles[key] = role
    roles_file = open(ROLES_FILE, mode='w')
    json.dump(assignable_roles, roles_file)

    if key in assignable_roles:
        await send_dm(ctx.author, f"Rolle {role} wurde hinzugefügt")
    else:
        await send_dm(ctx.author, f"Fehler beim Hinzufügen der Rolle {role}")


@bot.command(name="poll")
async def cmd_poll(ctx, question, *answers):
    await Poll(bot, question, answers, ctx.author.id).send_poll(ctx)


def load_roles():
    global assignable_roles
    roles_file = open(ROLES_FILE, mode='r')
    assignable_roles = json.load(roles_file)


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


@bot.command(name="link")
async def cmd_link(message):
    """ Sends link to invite others to Discord server in Chat. """

    await message.channel.send('Benutze bitte folgenden Link, um andere Studierende auf unseren Discord einzuladen: '
                               'http://fernuni-discord.dnns01.de')


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


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await unpin_message(message)


bot.run(TOKEN)
