import os

import discord


async def send_dm(user, message, embed=None):
    """ Send DM to a user/member """

    if type(user) is discord.User or type(user) is discord.Member:
        if user.dm_channel is None:
            await user.create_dm()

        await user.dm_channel.send(message, embed=embed)


def is_mod(ctx):
    author = ctx.author
    roles = author.roles

    for role in roles:
        if role.id == int(os.getenv("DISCORD_MOD_ROLE")):
            return True

    return False
