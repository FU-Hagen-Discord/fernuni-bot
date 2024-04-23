from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="voice", description="Sprachkanäle öffnen oder schließen")
    @app_commands.describe(state="Wähle, ob die Sprachkanäle geöffnet oder geschlossen werden sollen.")
    @app_commands.choices(state=[Choice(name="open", value="open"), Choice(name="close", value="close")])
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def cmd_voice(self, interaction: Interaction, state: Choice[str]):
        await interaction.response.defer(ephemeral=True)
        voice_channels = interaction.guild.voice_channels
        print(voice_channels[0].user_limit)
        if state.value == "open":
            for voice_channel in voice_channels:
                await voice_channel.edit(user_limit=0)
        elif state.value == "close":
            for voice_channel in voice_channels:
                await voice_channel.edit(user_limit=1)
        await interaction.edit_original_response(content="Status der Voice Channel erfolgreich geändert.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel != after.channel and after.channel and "Lerngruppen-Voicy" in after.channel.name:
            category_id = self.bot.get_settings(member.guild.id).learninggroup_voice_category_id
            bitrate = self.bot.get_settings(member.guild.id).voice_bitrate
            category = await self.bot.fetch_channel(category_id)
            voice_channels = category.voice_channels

            for voice_channel in voice_channels:
                if len(voice_channel.members) == 0:
                    return

            await category.create_voice_channel(f"Lerngruppen-Voicy-{len(voice_channels) + 1}", bitrate=bitrate)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
