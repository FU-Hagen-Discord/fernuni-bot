import os

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from tinydb import where


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_NEWS_CHANNEL"))
        self.news_role = int(os.getenv("DISCORD_NEWS_ROLE"))
        self.url = "https://www.fernuni-hagen.de/mi/studium/aktuelles/index.shtml"
        self.news_loop.start()

    @property
    def table(self):
        return self.bot.db.table('news')

    @tasks.loop(hours=1)
    async def news_loop(self):
        async with ClientSession() as session:
            async with session.get(self.url) as r:
                if r.status == 200:
                    content = await r.read()
                    soup = BeautifulSoup(content, "html.parser")
                    channel = await self.bot.fetch_channel(self.channel_id)

                    for news in soup.find("ul", attrs={"class": "fu-link-list"}).find_all("li"):
                        date = news.span.text
                        title = str(news.a.text)
                        link = news.a['href']

                        if link[0] == "/":
                            link = f"https://www.fernuni-hagen.de" + link

                        if not self.news.get(link):
                            await channel.send(
                                f":loudspeaker: <@&{self.news_role}> Neues aus der Fakultät vom {date} :loudspeaker: \n{title} \n{link}")
                            self.news[link] = date
                        else:
                            prev_date = self.news[link]
                            if date != prev_date:
                                await channel.send(
                                    f":loudspeaker: <@&{self.news_role}> Neues aus der Fakultät vom {date} :loudspeaker: \n{title} \n{link}")
                                self.news[link] = date

                    self.save_news()
