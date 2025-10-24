import logging
import os

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
PIN_EMOJI = "📌"

intents = Intents.all()
_log = logging.getLogger('discord.boty')


class Boty(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view_manager: ViewManager = ViewManager(self)

    async def setup_hook(self) -> None:
        await self.tree.sync()
        for extension in self.get_activated_extensions():
            await self.load_extension(f"extensions.{extension}")
            _log.info("Module %s loaded", extension)
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
        _log.info("Client started!")

    @staticmethod
    def get_settings(guild_id: int) -> Settings:
        return Settings.get(Settings.guild_id == guild_id)

    @staticmethod
    def dt_format():
        return "%d.%m.%Y %H:%M"
    
    @staticmethod
    def is_dev_mode_activated() -> bool:
        dev_mode = os.getenv('DISCORD_DEV_MODE')

        if dev_mode == None:
            return False

        return bool(dev_mode)    
    
    @staticmethod
    def get_activated_extensions():
        called_extensions = os.getenv('DISCORD_ACTIVATED_EXTENSIONS')

        if called_extensions == None:
            return ["welcome", "xkcd", "mod_mail", "module_information", "links", "news", "appointments", "text_commands"]
        
        activated_extensions = []
        for extension_name in called_extensions.split(","):
            activated_extensions.append(extension_name.strip().lower())

        return activated_extensions     

bot = Boty(command_prefix=')', help_command=None, activity=Game(ACTIVITY), owner_id=OWNER, intents=intents)


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
