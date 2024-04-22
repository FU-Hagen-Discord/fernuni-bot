from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

import models


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_loop.start()

    @tasks.loop(hours=1)
    async def news_loop(self):
        # ToDo: Add better handling for guild
        guild = models.Settings.select()[0].guild_id
        url = self.bot.get_settings(guild).news_url
        channel_id = self.bot.get_settings(guild).news_channel_id

        async with ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    content = await r.read()
                    soup = BeautifulSoup(content, "html.parser")
                    channel = await self.bot.fetch_channel(channel_id)

                    for news in soup.find("ul", attrs={"class": "fu-link-list"}).find_all("li"):
                        date = news.span.text
                        title = str(news.a.text)
                        link = news.a['href']

                        if link[0] == "/":
                            link = f"https://www.fernuni-hagen.de" + link

                        if news := models.News.get_or_none(link=link):
                            if news.date != date:
                                await self.announce_news(channel, date, title, link)
                                news.update(date=date).where(models.News.link == link).execute()
                        else:
                            await self.announce_news(channel, date, title, link)
                            models.News.create(link=link, date=date)

    async def announce_news(self, channel, date, title, link):
        guild = models.Settings.select()[0].guild_id
        news_role = self.bot.get_settings(guild).news_role_id
        await channel.send(
            f":loudspeaker: <@&{news_role}> Neues aus der Fakultät vom {date} :loudspeaker: \n{title} \n{link}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(News(bot))
