import random

import aiohttp
import discord
from discord import app_commands, Interaction
from discord.ext import commands


class Xkcd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="xkcd", description="Poste einen XKCD Comic. Zufällig oder deiner Wahl")
    @app_commands.describe(number="Nummer des XKCD Comics, den du posten möchtest.")
    @app_commands.guild_only()
    async def cmd_xkcd(self, interaction: Interaction, number: int = None):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:

            # Daten vom aktuellsten Comic holen, um max zu bestimmen
            async with session.get('http://xkcd.com/info.0.json') as request:
                data = await request.json()
            max = data['num']

            # Nummer übernehmen wenn vorhanden und zwischen 1 und max, sonst random Nummer wählen
            if number == 'latest':
                n = max
            else:
                try:
                    n = number if (number and 0 < int(number) <= max) else str(random.randint(1, max))
                except ValueError:
                    n = str(random.randint(1, max))

            # Daten zum Bild holen
            async with session.get(f'http://xkcd.com/{n}/info.0.json') as request:
                n_data = await request.json()

        img = n_data['img']
        num = n_data['num']
        title = n_data['title']
        text = n_data['alt']

        # Comic embedden
        embed = discord.Embed(title=f"xkcd #{num}: {title}", description=text, url=f"https://xkcd.com/{num}")
        embed.set_image(url=img)

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Xkcd(bot))
