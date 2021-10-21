import random
import aiohttp

import disnake
from disnake.ext import commands
from cogs.help import help


class Xkcd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @help(
        brief="Ruft einen xkcd Comic ab.",
        syntax="!xkcd <number>",
        parameters={
            "number": "*(optional)* Entweder die Nummer eines spezifischen xkcd Comics, oder `latest`, für den aktuellsten.",
        },
    )
    @commands.command(name="xkcd")
    async def cmd_xkcd(self, ctx, number=None):

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
        e = disnake.Embed()
        e.set_image(url=img)
        e.url = img
        e.title = f'xkcd #{num}'
        e.add_field(name=title, value=text)
        e.set_footer(text='https://xkcd.com', icon_url='https://xkcd.com/s/0b7742.png')

        await ctx.send(embed=e)
