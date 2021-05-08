import random
import requests

import discord
from discord.ext import commands


class Xkcd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="xkcd")
    async def cmd_xkcd(self, ctx):
        # Daten vom aktuellsten Comic holen, um max zu bestimmen
        data = requests.get('http://xkcd.com/info.0.json')
        data_json = data.json()
        max = data_json['num']

        # Daten von random Comic holen
        r = str(random.randint(1,max))
        r_data = requests.get(f'http://xkcd.com/{r}/info.0.json')
        r_data_json = r_data.json()

        # Link zum Bild posten
        img = r_data_json['img']
        num = r_data_json['num']
        await ctx.send(f'xkcd #{num} [https://xkcd.com]\n {img}')
