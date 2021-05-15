import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

# from welcome_cog import WelcomeCog
from appointments_cog import AppointmentsCog
from armin import Armin
from christmas_cog import ChristmasCog
from easter_cog import EasterCog
from github import Github
from help.help import Help
from learninggroups import LearningGroups
from links_cog import LinksCog
from news_cog import NewsCog
from poll_cog import PollCog
from roles_cog import RolesCog
from support_cog import SupportCog
from text_commands_cog import TextCommandsCog
# from change_log import ChangeLogCog
from voice_cog import VoiceCog
from welcome_cog import WelcomeCog

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
bot.add_cog(LearningGroups(bot))
bot.add_cog(Help(bot))
bot.add_cog(Github(bot))


def get_reaction(reactions):
    """ Returns the reaction, that is equal to the specified PIN_EMOJI,
    or if that reaction does not exist in list of reactions, None will be returned"""

    for reaction in reactions:
        if reaction.emoji == PIN_EMOJI:
            return reaction
    return None

async def pin_message(message):
    """ Pin the given message, if it is not already pinned """

    if not message.pinned:
        await message.pin()


async def unpin_message(message):
    """ Unpin the given message, if it is pinned, and it has no pin reaction remaining. """

    if message.pinned:
        reaction = get_reaction(message.reactions)
        if reaction is None:
            await message.unpin()


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
