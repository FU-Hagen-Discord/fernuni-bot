import os
from typing import List

import discord
from discord import Intents, Game, app_commands, Interaction
from discord.ext import commands
from dotenv import load_dotenv

from view_manager import ViewManager

# .env file is necessary in the same directory, that contains several strings.
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD'))
ACTIVITY = os.getenv('DISCORD_ACTIVITY')
OWNER = int(os.getenv('DISCORD_OWNER'))
ROLES_FILE = os.getenv('DISCORD_ROLES_FILE')
HELP_FILE = os.getenv('DISCORD_HELP_FILE')
PIN_EMOJI = "📌"

intents = Intents.all()
extensions = ["appointments", "github", "news", "mod_mail", "voice", "welcome", "xkcd"]


class Boty(commands.Bot):
    def __init__(self, *args, initial_extensions: List[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.is_prod = os.getenv("DISCORD_PROD") == "True"
        self.initial_extensions: List[str] = initial_extensions
        self.view_manager: ViewManager = ViewManager(self)
        self.persistent_views_added: bool = False

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            await self.load_extension(f"extensions.{extension}")
            print(f"➕ Module {extension}")
        await self.sync_slash_commands_for_guild(GUILD_ID)

    async def sync_slash_commands_for_guild(self, guild_id):
        guild = discord.Object(id=guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        self.view_manager.on_ready()
        if not self.persistent_views_added:
            if timer_cog := self.get_cog("Timer"):
                self.add_view(timer_cog.get_view())
        print("✅ Client started!")

    @app_commands.command(name="sync")
    @app_commands.guild_only()
    async def cmd_sync(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.sync_slash_commands_for_guild(GUILD_ID)
        await interaction.followup.send("Synchronisiert!")


bot = Boty(command_prefix='!', help_command=None, activity=Game(ACTIVITY), owner_id=OWNER, intents=intents,
           initial_extensions=extensions)


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


bot.run(TOKEN)
