import os

import discord
from dotenv import load_dotenv

# .env file is necessary in the same directory, that contains Token and guild.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
PIN_EMOJI = "📌"
client = discord.Client(activity=discord.Game(ACTIVITY))


# Returns an guild object, that matches the id specified in GUILD.
# This guild is the FU Hagen Informatik/Mathematik guild.
def get_guild():
    for guild in client.guilds:
        if guild.id == GUILD:
            return guild

    return None


# Get the key for a given role. This role is used for adding or removing a role from a user.
def get_key(role):
    if role.name == "B.Sc. Informatik":
        return "BI"
    elif role.name == "B.Sc. Mathematik":
        return "BM"
    elif role.name == "B.Sc. Wirtschaftsinformatik":
        return "BWI"
    elif role.name == "M.Sc. Informatik":
        return "MI"
    elif role.name == "M.Sc. Praktische Informatik":
        return "MPI"
    elif role.name == "M.Sc. Mathematik":
        return "MM"
    elif role.name == "M.Sc. Wirtschaftsinformatik":
        return "MWI"
    elif role.name == "Pink":
        return "PNK"
    elif role.name == "Türkis":
        return "TKS"
    elif role.name == "Orange":
        return "ONG"
    elif role.name == "Lila":
        return "LLA"
    elif role.name == "Grün":
        return "GRN"
    elif role.name == "Blau":
        return "BLU"


# Get all roles that are available at the guild.
def get_guild_roles():
    guild = get_guild()
    if guild is not None:
        roles = {}
        for role in guild.roles:
            role_key = get_key(role)
            if role_key is not None:
                roles[role_key] = role

        return roles

    return None


# Get all roles assigned to a member.
def get_members_roles(user):
    guild = get_guild()
    if (type(user) is discord.User or type(user) is discord.Member) and guild is not None:
        return guild.get_member(user.id).roles

    return None


# Returns the reaction, that is equal to the specified PIN_EMOJI,
# or if that reaction does not exist in list of reactions, None will be returned
def get_reaction(reactions):
    for reaction in reactions:
        if reaction.emoji == PIN_EMOJI:
            return reaction

    return None


# Send DM to a user/member
async def send_dm(user, message):
    if type(user) is discord.User or type(user) is discord.Member:
        if user.dm_channel is None:
            await user.create_dm()

        await user.dm_channel.send(message)


# Send help message as DM
async def fu_help(message):
    answer = f'Ich bin der Fernuni-Bot. Ich kann Rollen zuweisen/entfernen. \n\n'
    answer += f'Folgende Kommandos stehen zur verfügung:\n'
    answer += f'`=fu-help` - Zeigt diesen Hilfetext an\n'
    answer += f'`=fu-all-roles` - Zeigt alle verfügbaren Rollen an, die ich dir zuweisen/entfernen kann.\n'
    answer += f'`=fu-my-roles` - Zeigt alle Rollen an, die dir momentan zugewiesen sind.\n'
    answer += f'`=fu-add-roles` - Mit diesem Kommando, gefolgt von einer Liste von Rollen, ' \
              f'weise ich dir diese Rollen zu.\n'
    answer += f'`=fu-remove roles` - Mit diesem Kommendo, gefolgt von einer Liste von Rollen, ' \
              f'entferne ich dir diese Rollen.\n\n'
    answer += f'Hinweise für die Nutzung der Kommandos zum Zuweisen/Entfernen von Rollen:\n'
    answer += f'In der Liste der verfügbaren Rollen siehst du in eckigen Klammern  einen Schlüssel für die jeweilige ' \
              f'Rolle, die für diese Kommandos zu verwenden ist. \n'
    answer += f'Beispiel: \n[BI] B.Sc. Informatik \n[MM] M.Sc. Mathematik \n'
    answer += f'`=fu-add-roles BI` fügt die Rolle B.Sc. Informatik hinzu. \n'
    answer += f'`=fu-remove-roles BI MM` entfernt die Rollen B.Sc. Informatik und M.Sc Mathematik. \n'

    await send_dm(message.author, answer)


# Send all available roles that can be assigned to a member by this bot as DM
async def fu_all_roles(message):
    roles = get_guild_roles()
    answer = "Verfügbare Rollen: \n"
    for key, role in roles.items():
        answer += f'[{key}] {role.name}\n'

    await send_dm(message.author, answer)


# Send the roles assigned to a member as DM.
async def fu_my_roles(message):
    my_roles = get_members_roles(message.author)
    answer = "Dir zugewiesene Rollen:\n"

    if my_roles is not None:
        for role in my_roles:
            key = get_key(role)
            if key is not None:
                answer += f'[{key}] {role.name} \n'

    await send_dm(message.author, answer)


# Add or remove roles assigned to a member. Multiple roles can be added with one command, or removed.
async def fu_modify_roles(message, add):
    msg = message.content
    splitted_msg = msg.split(" ")
    guild = get_guild()

    if guild is not None:
        member = guild.get_member(message.author.id)

        if len(splitted_msg) > 1:
            roles = get_guild_roles()
            for key in splitted_msg[1:]:
                if key in roles:
                    role = roles[key]
                    if add:
                        try:
                            await member.add_roles(role)
                            await send_dm(message.author, f'Dir wurde die Rolle {role.name} hinzugefügt')
                        except Exception:
                            await send_dm(message.author, f'Fehler bei der Zuweisung der Rolle {role.name}')
                    else:
                        try:
                            await member.remove_roles(role)
                            await send_dm(message.author, f'Dir wurde die Rolle {role.name} entfernt')
                        except Exception:
                            await send_dm(message.author, f'Fehler bei der Entfernung der Rolle {role.name}')


# Pin the given message, if it is not already pinned
async def pin_message(message):
    if not message.pinned:
        await message.pin()


# Unpin the given message, if it is pinned, and it has no pin reaction remaining.
async def unpin_message(message):
    if message.pinned:
        reaction = get_reaction(message.reactions)
        if reaction is None:
            await message.unpin()


@client.event
async def on_ready():
    print("Client started!")


@client.event
async def on_message(message):
    msg = message.content

    if message.author == client.user:
        return

    if msg.startswith("=fu-help"):
        await fu_help(message)
    elif msg.startswith("=fu-all-roles"):
        await fu_all_roles(message)
    elif msg.startswith("=fu-my-roles"):
        await fu_my_roles(message)
    elif msg.startswith("=fu-add-roles"):
        await fu_modify_roles(message, add=True)
    elif msg.startswith("=fu-remove-roles"):
        await fu_modify_roles(message, add=False)
    elif msg == "=fu-link":
        await message.channel.send(
            "Um andere auf diesen Discord einzuladen, nutze bitte folgenden Link: http://fernuni-discord.dnns01.de")


@client.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await client.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await pin_message(message)


@client.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await client.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await unpin_message(message)


client.run(TOKEN)
