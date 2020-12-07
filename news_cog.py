import json
import os

import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks


class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv("DISCORD_NEWS_CHANNEL"))
        self.news_role = int(os.getenv("DISCORD_NEWS_ROLE"))
        self.url = "https://www.fernuni-hagen.de/mi/studium/aktuelles/index.shtml"
        self.news = {}
        self.load_news()
        self.news_loop.start()

    def load_news(self):
        news_file = open("news.json", mode="r")
        self.news = json.load(news_file)

    def save_news(self):
        news_file = open("news.json", mode="w")
        json.dump(self.news, news_file)

    @tasks.loop(minutes=1)
    async def news_loop(self):
        req = requests.get(self.url)
        soup = BeautifulSoup(req.content, "html.parser")
        channel = await self.bot.fetch_channel(self.channel_id)

        for news in soup.find("ul", attrs={"class": "fu-link-list"}).find_all("li"):
            date = news.span.text
            title = str(news.a.text)
            link = news.a['href']

            if link[0] == "/":
                link = f"https://www.fernuni-hagen.de" + link

            if not self.news.get(link):
                self.news[link] = date
                await channel.send(
                    f":loudspeaker: <@&{self.news_role}> Neues aus der Fakultät vom {date} :loudspeaker: \n{title} \n{link}")
            else:
                prev_date = self.news[link]
                if date != prev_date:
                    self.news[link] = date
                    await channel.send(
                        f":loudspeaker: Neues aus der Fakultät vom {date} :loudspeaker: \n{title} \n{link}")

        self.save_news()
