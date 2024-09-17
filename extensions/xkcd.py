import random
from typing import Dict, Any

import aiohttp
import discord
from aiohttp import ClientSession
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

            latest = (await self.get_info(session)).get("num")

            # Nummer übernehmen wenn vorhanden und zwischen 1 und max, sonst random Nummer wählen
            n = number if number and (0 < number <= latest) else random.randint(1, latest)

            # Daten zum Bild holen
            if info := await self.get_info(session, number=n):
                img = info["img"]
                num = info["num"]
                title = info["title"]
                text = info["alt"]

                # Comic embedden
                embed = discord.Embed(title=f"xkcd #{num}: {title}", description=text, url=f"https://xkcd.com/{num}")
                if n != number:
                    embed.set_footer(text="Du erhältst einen zufälligen Comic, da du entweder keine Nummer eingegeben hast, oder die von dir eingegebene Nummer ungültig war. Viel Spaß :)")
                embed.set_image(url=img)

                await interaction.edit_original_response(embed=embed)
                return

        await interaction.edit_original_response(content="Leider ist beim Abrufen des xkcd Comics ein Fehler aufgetreten.")

    @staticmethod
    async def get_info(session: ClientSession, number: int = None) -> Dict[str, Any]:
        url = f"http://xkcd.com/{number}/info.0.json" if number else "http://xkcd.com/info.0.json"
        async with session.get(url) as request:
            if request.status == 200:
                return await request.json()

        return {}


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Xkcd(bot))
