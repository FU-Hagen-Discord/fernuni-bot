import os

import discord
from discord.ext import commands
from dislash import *
from dotenv import load_dotenv
from tinydb import TinyDB

from cogs import appointments, armin, calmdown, christmas, easter, github, help, learninggroups, links, \
    module_information, news, polls, roles, support, text_commands, voice, welcome, xkcd, timer

# .env file is necessary in the same directory, that contains several strings.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
OWNER = int(os.getenv('DISCORD_OWNER'))
ROLES_FILE = os.getenv('DISCORD_ROLES_FILE')
HELP_FILE = os.getenv('DISCORD_HELP_FILE')
DISCORD_DB = os.getenv('DISCORD_DB')
CATEGORY_LERNGRUPPEN = os.getenv("DISCORD_CATEGORY_LERNGRUPPEN")
PIN_EMOJI = "📌"


class Boty(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.add_cog(armin.Armin(self))
        self.add_cog(learninggroups.LearningGroups(self))
        self.add_cog(module_information.ModuleInformation(self))
        self.add_cog(xkcd.Xkcd(self))
        self.add_cog(help.Help(self))
        self.add_cog(calmdown.Calmdown(self))
        self.add_cog(github.Github(self))
        # self.add_cog(ChangeLogCog(self))
        self.db = TinyDB(DISCORD_DB)

    async def on_ready(self):
        print("Client started!")

SlashClient(bot, show_warnings=True)  # Stellt den Zugriff auf die Buttons bereit

bot = Boty(command_prefix='!', help_command=None, activity=discord.Game(ACTIVITY), owner_id=OWNER,
           intents=discord.Intents.all())


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if not message.pinned:
            await message.pin()


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == PIN_EMOJI:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if message.pinned and not discord.utils.get(message.reactions, emoji__name=PIN_EMOJI):
            await message.unpin()


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
