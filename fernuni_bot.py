import json
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

# from welcome_cog import WelcomeCog
import utils
from appointments_cog import AppointmentsCog
from christmas_cog import ChristmasCog
from links_cog import LinksCog
from news_cog import NewsCog
from poll_cog import PollCog
from roles_cog import RolesCog
from support_cog import SupportCog
from text_commands_cog import TextCommandsCog
from welcome_cog import WelcomeCog
# from change_log import ChangeLogCog
from voice_cog import VoiceCog
from easter_cog import EasterCog
from armin import Armin

# .env file is necessary in the same directory, that contains several strings.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
OWNER = int(os.getenv('DISCORD_OWNER'))
ROLES_FILE = os.getenv('DISCORD_ROLES_FILE')
HELP_FILE = os.getenv('DISCORD_HELP_FILE')
CATEGORY_LERNGRUPPEN = os.getenv("DISCORD_CATEGORY_LERNGRUPPEN")
PIN_EMOJI = "📌"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', help_command=None, activity=discord.Game(ACTIVITY), owner_id=OWNER,
                   intents=intents)
bot.add_cog(AppointmentsCog(bot))
bot.add_cog(TextCommandsCog(bot))
bot.add_cog(PollCog(bot))
bot.add_cog(RolesCog(bot))
bot.add_cog(WelcomeCog(bot))
bot.add_cog(ChristmasCog(bot))
bot.add_cog(SupportCog(bot))
bot.add_cog(NewsCog(bot))
bot.add_cog(LinksCog(bot))
# bot.add_cog(ChangeLogCog(bot))
bot.add_cog(VoiceCog(bot))
bot.add_cog(EasterCog(bot))
bot.add_cog(Armin(bot))


def get_reaction(reactions):
    """ Returns the reaction, that is equal to the specified PIN_EMOJI,
    or if that reaction does not exist in list of reactions, None will be returned"""

    for reaction in reactions:
        if reaction.emoji == PIN_EMOJI:
            return reaction
    return None


@bot.command(name="help")
async def cmd_help(ctx):
    """ Send help message as DM """

    help_file = open(HELP_FILE, mode='r')
    help_dict = json.load(help_file)
    embed = discord.Embed.from_dict(help_dict)
    await utils.send_dm(ctx.author, "", embed=embed)


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


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

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
