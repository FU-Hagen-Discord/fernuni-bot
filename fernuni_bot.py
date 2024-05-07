import os
from typing import List

import discord
from discord import Intents, Game, Thread
from discord.app_commands import Group
from discord.ext import commands
from dotenv import load_dotenv

from models import Settings
from view_manager import ViewManager

# .env file is necessary in the same directory, that contains several strings.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
OWNER = int(os.getenv('DISCORD_OWNER'))
# ROLES_FILE = os.getenv('DISCORD_ROLES_FILE')
# HELP_FILE = os.getenv('DISCORD_HELP_FILE')
PIN_EMOJI = "📌"

intents = Intents.all()
extensions = ["appointments", "news", "mod_mail", "voice", "welcome", "xkcd", "timer", "polls",
              "text_commands", "links", "module_information", "learninggroups"]


class Boty(commands.Bot):
    def __init__(self, *args, initial_extensions: List[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_extensions: List[str] = initial_extensions
        self.view_manager: ViewManager = ViewManager(self)

    async def setup_hook(self) -> None:
        await self.tree.sync()
        for extension in self.initial_extensions:
            await self.load_extension(f"extensions.{extension}")
            print(f"➕ Module {extension}")
        await self.sync_slash_commands_for_guild(GUILD_ID)

    async def sync_slash_commands_for_guild(self, guild_id):
        guild = discord.Object(id=guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def get_slash_commands_for_guild(self, guild_id, command=None):
        guild = discord.Object(id=guild_id)
        commands = [self.tree.get_command(command, guild=guild)] if command else self.tree.get_commands(guild=guild)
        commands.sort(key=lambda e: f"a{e.name}" if isinstance(e, Group) else f"b{e.name}")
        return commands

    async def on_ready(self):
        self.view_manager.on_ready()
        print("✅ Client started!")

    @staticmethod
    def get_settings(guild_id: int) -> Settings:
        return Settings.get(Settings.guild_id == guild_id)

    @staticmethod
    def dt_format():
        return "%d.%m.%Y %H:%M"


bot = Boty(command_prefix='!', help_command=None, activity=Game(ACTIVITY), owner_id=OWNER, intents=intents,
           initial_extensions=extensions)


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
async def on_thread_create(thread: Thread) -> None:
    thread_notification_role_id = bot.get_settings(thread.guild.id).thread_notification_role_id
    msg = await thread.send(f"<@&{thread_notification_role_id}>")
    await msg.delete()


bot.run(TOKEN)
