import os

import disnake
from disnake.ext import commands
from dotenv import load_dotenv

from cogs import appointments, calmdown, christmas, easter, github, help, learninggroups, links, \
    news, polls, roles, support, text_commands, voice, welcome, xkcd, module_information
# , timer

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

intents = disnake.Intents.default()
intents.members = True


class Boty(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', help_command=None, activity=disnake.Game(ACTIVITY), owner_id=OWNER,
                         intents=intents)
        self.add_cog(appointments.Appointments(self))
        self.add_cog(text_commands.TextCommands(self))
        self.add_cog(polls.Polls(self))
        self.add_cog(roles.Roles(self))
        self.add_cog(welcome.Welcome(self))
        self.add_cog(christmas.Christmas(self))
        self.add_cog(support.Support(self))
        self.add_cog(news.News(self))
        self.add_cog(links.Links(self))
        self.add_cog(voice.Voice(self))
        self.add_cog(easter.Easter(self))
        self.add_cog(learninggroups.LearningGroups(self))
        self.add_cog(module_information.ModuleInformation(self))
        self.add_cog(xkcd.Xkcd(self))
        self.add_cog(help.Help(self))
        self.add_cog(calmdown.Calmdown(self))
        self.add_cog(github.Github(self))
        # self.add_cog(timer.Timer(self))


bot = Boty()


# bot.add_cog(ChangeLogCog(bot))

# SlashClient(bot, show_warnings=True)  # Stellt den Zugriff auf die Buttons bereit


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
