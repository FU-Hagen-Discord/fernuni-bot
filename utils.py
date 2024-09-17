import os
import re
from datetime import datetime

from discord import ButtonStyle, Embed, User, Member
from discord.ext.commands import Context
from dotenv import load_dotenv

from views.dialog_view import DialogView

load_dotenv()
DATE_TIME_FMT = os.getenv("DISCORD_DATE_TIME_FORMAT")
MAX_MESSAGE_LEN = 2000

async def send_dm(user, message, embed=None):
    """ Send DM to a user/member """

    try:
        if type(user) is User or type(user) is Member:
            if user.dm_channel is None:
                await user.create_dm()

            return await user.dm_channel.send(message, embed=embed)
    except:
        print(f"Cannot send DM to {user} with text: {message}")


# def is_mod(context_or_member):
#     if isinstance(context_or_member, Context):
#         author = context_or_member.author
#     else:
#         author = context_or_member
#     roles = author.roles
#
#     for role in roles:
#         if role.id == int(os.getenv("DISCORD_MOD_ROLE")):
#             return True
#
#     return False

def is_mod(user: Member, bot):
    if user.get_role(int(os.getenv("DISCORD_MOD_ROLE"))):
        return True

    return False


def is_valid_time(time):
    return re.match(r"^\d+[mhd]?$", time)


def to_minutes(time):
    if time[-1:] == "m":
        return int(time[:-1])
    elif time[-1:] == "h":
        h = int(time[:-1])
        return h * 60
    elif time[-1:] == "d":
        d = int(time[:-1])
        h = d * 24
        return h * 60

    return int(time)


async def confirm(channel, title, description, message="", custom_prefix="", callback=None):
    embed = Embed(title=title,
                          description=description,
                          color=19607)
    return await channel.send(message, embed=embed, view=DialogView([
        {"emoji": "👍", "custom_id": f"{custom_prefix}_yes", "style": ButtonStyle.green},
        {"emoji": "👎", "custom_id": f"{custom_prefix}_no", "style": ButtonStyle.red},
    ]))


def date_to_string(date: datetime):
    return date.strftime(DATE_TIME_FMT)


def date_from_string(date: str):
    return datetime.strptime(date, DATE_TIME_FMT)


async def files_from_attachments(attachments):
    files = []
    for attachment in attachments:
        files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

    return files
