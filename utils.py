import os

import disnake
import re

from disnake import ButtonStyle

from views.dialog_view import DialogView


async def send_dm(user, message, embed=None):
    """ Send DM to a user/member """

    if type(user) is disnake.User or type(user) is disnake.Member:
        if user.dm_channel is None:
            await user.create_dm()

        return await user.dm_channel.send(message, embed=embed)


def is_mod(ctx):
    author = ctx.author
    roles = author.roles

    for role in roles:
        if role.id == int(os.getenv("DISCORD_MOD_ROLE")):
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
    embed = disnake.Embed(title=title,
                          description=description,
                          color=19607)
    return await channel.send(message, embed=embed, view=DialogView([
        {"emoji": "👍", "custom_id": f"{custom_prefix}_yes", "style": ButtonStyle.green},
        {"emoji": "👎", "custom_id": f"{custom_prefix}_no", "style": ButtonStyle.red},
    ]))
