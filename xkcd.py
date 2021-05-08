import random
import requests

import discord
from discord.ext import commands


class Xkcd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="xkcd")
    async def cmd_xkcd(self, ctx, number=None):
        # Daten vom aktuellsten Comic holen, um max zu bestimmen
        data = requests.get('http://xkcd.com/info.0.json')
        data_json = data.json()
        max = data_json['num']

        # Nummer übernehmen wenn vorhanden und zwischen 1 und max, sonst random Nummer wählen
        if number == 'latest':
            n = max
        else:
            try:
                n = number if (number and 0 < int(number) <= max) else str(random.randint(1, max))
            except ValueError:
                n = str(random.randint(1, max))

        # Daten zum Bild holen
        n_data = requests.get(f'http://xkcd.com/{n}/info.0.json')
        n_data_json = n_data.json()

        img = n_data_json['img']
        num = n_data_json['num']
        title = n_data_json['title']
        text = n_data_json['alt']

        # Comic embedden
        e = discord.Embed()
        e.set_image(url=img)
        e.url = img
        e.title = f'xkcd #{num}'
        e.add_field(name=title, value=text)
        e.set_footer(text='https://xkcd.com', icon_url='https://xkcd.com/s/0b7742.png')

        await ctx.send(embed=e)
