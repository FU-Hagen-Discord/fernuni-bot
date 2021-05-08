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

        # Link zum Bild holen
        img = r_data_json['img']
        num = r_data_json['num']

        # Comic embedden
        e = discord.Embed()
        e.set_image(url=img)
        e.url = img
        e.title = f'xkcd #{num}'
        e.set_footer(text='https://xkcd.com', icon_url='https://xkcd.com/s/0b7742.png')

        await ctx.send(embed=e)
