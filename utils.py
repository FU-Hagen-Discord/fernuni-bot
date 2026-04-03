import os

from discord import ButtonStyle, Embed, User, Member, app_commands
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


def is_mod(user: Member):
    if user.get_role(int(os.getenv("DISCORD_MOD_ROLE"))):
        return True

    return False


def mod_only():
    def decorator(command):
        command = app_commands.checks.has_role("Mod")(command)
        return app_commands.default_permissions(manage_channels=True)(command)

    return decorator


async def confirm(channel, title, description, message="", custom_prefix="", callback=None):
    embed = Embed(title=title,
                  description=description,
                  color=19607)
    return await channel.send(message, embed=embed, view=DialogView([
        {"emoji": "👍", "custom_id": f"{custom_prefix}_yes", "style": ButtonStyle.green},
        {"emoji": "👎", "custom_id": f"{custom_prefix}_no", "style": ButtonStyle.red},
    ]))
