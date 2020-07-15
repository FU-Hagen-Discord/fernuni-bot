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
    elif role.name == "B.Sc. Mathematisch-Technische Softwareentwicklung":
        return "BMTS"
    elif role.name == "M.Sc. Informatik":
        return "MI"
    elif role.name == "M.Sc. Praktische Informatik":
        return "MPI"
    elif role.name == "M.Sc. Mathematik":
        return "MM"
    elif role.name == "M.Sc. Wirtschaftsinformatik":
        return "MWI"
    elif role.name.startswith("Farbe-"):
        return role.name[6:9]


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
async def send_dm(user, message, embed=None):
    if type(user) is discord.User or type(user) is discord.Member:
        if user.dm_channel is None:
            await user.create_dm()

        await user.dm_channel.send(message, embed=embed)


# Send help message as DM
async def fu_help(message):
    embed = discord.Embed(title="Fernuni-Bot Hilfe",
                          description="Mit mir kannst du auf folgende Weise interagieren:",
                          color=0x004c97)

    embed.set_thumbnail(
        url="https://cdn.discordapp.com/avatars/697842294279241749/c7d3063f39d33862e9b950f72ab71165.webp?size=1024")
    embed.add_field(name="!help", value='Hilfe anzeigen', inline=False)
    embed.add_field(name="!link", value='Einladungslink für diesen Discord-Server anzeigen.', inline=False)
    embed.add_field(name="!stats", value='Nutzerstatistik anzeigen', inline=False)
    embed.add_field(name="!all-roles", value='Alle verfügbaren Rollen anzeigen', inline=False)
    embed.add_field(name="!my-roles", value='Dir zugewiesene Rollen anzeigen', inline=False)
    embed.add_field(name="!add-roles ROLE1 ...", value='Eine oder mehrere Rollen hinzufügen', inline=False)
    embed.add_field(name="!remove-roles ROLE1 ...", value='Eine oder mehrere zugewiesene Rollen entfernen',
                    inline=False)
    embed.add_field(name='\u200B', value='\u200B', inline=False)
    embed.add_field(name="Benutzung Rollenbezogener Kommandos",
                    value='Der Aufruf von `!all-roles` oder `!my-roles` gibt eine Liste der Rollen aus, die '
                          'folgendermaßen aufgebaut ist: `[KEY] ROLLENNAME`. \u000ABeispiel: \u000A'
                          '[BWI] B.Sc. Wirtschaftsinformatik \u000A[BM] B.Sc. Mathematik \u000A'
                          '[BI] B.Sc. Informatik \u000A\u000ABei der Verwendung von `!add-roles` und `!remove-roles` '
                          'kann nun eine Liste von Keys übergeben werden, um sich selbst diese Rollen hinzuzufügen, '
                          'oder zu entfernen. Möchte man sich also nun selbst die Rollen B.Sc. Informatik und '
                          'B.Sc. Mathematik hinzufügen, gibt man folgendes kommando ein: `!add-roles BI BM`',
                    inline=False)

    await send_dm(message.author, "", embed=embed)


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


# Sends link to invite others to Discord server in Chat.
async def fu_link(message):
    await message.channel.send('Benutze bitte folgenden Link, um andere Studierende auf unseren Discord einzuladen: '
                               'http://fernuni-discord.dnns01.de')


# Sends stats in Chat.
async def fu_stats(message):
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


# Pin the given message, if it is not already pinned
async def pin_message(message):
    if not message.pinned:
        await message.pin()
        await message.channel.send(f'Folgende Nachricht wurde gerade angepinnt: {message.jump_url}')


# Unpin the given message, if it is pinned, and it has no pin reaction remaining.
async def unpin_message(message):
    if message.pinned:
        reaction = get_reaction(message.reactions)
        if reaction is None:
            await message.unpin()
            await message.channel.send(f'Folgende Nachricht wurde gerade losgelöst: {message.jump_url}')


@client.event
async def on_ready():
    print("Client started!")


@client.event
async def on_message(message):
    msg = message.content

    if message.author == client.user:
        return

    if msg.startswith("!help"):
        await fu_help(message)
    elif msg.startswith("!all-roles"):
        await fu_all_roles(message)
    elif msg.startswith("!my-roles"):
        await fu_my_roles(message)
    elif msg.startswith("!add-roles"):
        await fu_modify_roles(message, add=True)
    elif msg.startswith("!remove-roles"):
        await fu_modify_roles(message, add=False)
    elif msg == "!link":
        await fu_link(message)
    elif msg == "!stats":
        await fu_stats(message)


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
