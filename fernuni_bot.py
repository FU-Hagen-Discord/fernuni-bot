import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

# from welcome_cog import WelcomeCog
from cogs.appointments import Appointments
from cogs.armin import Armin
from cogs.calmdown import Calmdown
from cogs.christmas import Christmas
from cogs.easter import Easter
from cogs.github import Github
from cogs.help import Help
from cogs.learninggroups import LearningGroups
from cogs.links import Links
from cogs.module_information import ModuleInformation
from cogs.news import News
from cogs.poll import Poll
from cogs.roles import Roles
from cogs.support import Support
from cogs.text_commands import TextCommands
# from change_log import ChangeLogCog
from cogs.voice import Voice
from cogs.welcome import Welcome
from cogs.xkcd import Xkcd


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
bot.add_cog(Appointments(bot))
bot.add_cog(TextCommands(bot))
bot.add_cog(Poll(bot))
bot.add_cog(Roles(bot))
bot.add_cog(Welcome(bot))
bot.add_cog(Christmas(bot))
bot.add_cog(Support(bot))
bot.add_cog(News(bot))
bot.add_cog(Links(bot))
# bot.add_cog(ChangeLogCog(bot))
bot.add_cog(Voice(bot))
bot.add_cog(Easter(bot))
bot.add_cog(Armin(bot))
bot.add_cog(LearningGroups(bot))
bot.add_cog(ModuleInformation(bot))
bot.add_cog(Xkcd(bot))
bot.add_cog(Help(bot))
bot.add_cog(Calmdown(bot))
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
    if before.channel != after.channel and after.channel and "Lerngruppen-Voicy" in after.channel.name:
        category = await bot.fetch_channel(CATEGORY_LERNGRUPPEN)
        voice_channels = category.voice_channels

        for voice_channel in voice_channels:
            if len(voice_channel.members) == 0:
                return

        await category.create_voice_channel(f"Lerngruppen-Voicy-{len(voice_channels) + 1}", bitrate=256000)


bot.run(TOKEN)
