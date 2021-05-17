import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs import appointments, armin, calmdown, christmas, easter, github, help, learninggroups, links, \
    module_information, news, polls, roles, support, text_commands, voice, welcome, xkcd

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
bot.add_cog(appointments.Appointments(bot))
bot.add_cog(text_commands.TextCommands(bot))
bot.add_cog(polls.Polls(bot))
bot.add_cog(roles.Roles(bot))
bot.add_cog(welcome.Welcome(bot))
bot.add_cog(christmas.Christmas(bot))
bot.add_cog(support.Support(bot))
bot.add_cog(news.News(bot))
bot.add_cog(links.Links(bot))
bot.add_cog(voice.Voice(bot))
bot.add_cog(easter.Easter(bot))
bot.add_cog(armin.Armin(bot))
bot.add_cog(learninggroups.LearningGroups(bot))
bot.add_cog(module_information.ModuleInformation(bot))
bot.add_cog(xkcd.Xkcd(bot))
bot.add_cog(help.Help(bot))
bot.add_cog(calmdown.Calmdown(bot))
bot.add_cog(github.Github(bot))


# bot.add_cog(ChangeLogCog(bot))


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
