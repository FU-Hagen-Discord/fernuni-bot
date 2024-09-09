from typing import Optional
from xml.etree.ElementTree import Element

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord import errors, Embed
from discord.ext import commands, tasks
from defusedxml.ElementTree import fromstring

from models import NewsFeed, NewsArticle, Settings


def find_text(parent: Element, tag_name: str):
    element = parent.find(tag_name)
    if element is not None:
        return element.text

    return None


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_loop.start()

    @tasks.loop(hours=1)
    async def news_loop(self):
        for feed in NewsFeed.select():
            match feed.type:
                case "RSS":
                    await self.parse_rss(feed)

    async def parse_rss(self, feed: NewsFeed):
        async with ClientSession() as session:
            async with session.get(feed.url) as response:
                if response.status == 200:
                    content = str(await response.read(), encoding='utf-8')
                    root = fromstring(content)
                    for article in root.iter('item'):
                        if news_article := await self.parse_article_rss(article, feed):
                            await self.announce_news(news_article)

    @staticmethod
    async def parse_article_rss(article: Element, feed: NewsFeed) -> Optional[NewsArticle]:
        title = find_text(article, "title")
        description = find_text(article, "description")
        link = find_text(article, "link")
        pub_date = find_text(article, "pubDate")

        if news_article := NewsArticle.get_or_none(link=link):
            if news_article.pub_date != pub_date:
                news_article.update(title=title, description=description, pub_date=pub_date).where(
                    NewsArticle.link == link).execute()
                return NewsArticle.get_or_none(link=link)
            else:
                return None
        else:
            return NewsArticle.create(news_feed=feed, title=title, description=description, link=link, pub_date=pub_date)

    async def announce_news(self, news_article: NewsArticle):
        settings = news_article.news_feed.settings
        news_role = settings.news_role_id
        try:
            channel = await self.bot.fetch_channel(settings.news_channel_id)
            embed = Embed(title=news_article.title, url=news_article.link)
            if news_article.description:
                embed.description = news_article.description
            await channel.send(
                f":loudspeaker: <@&{news_role}> Neues aus der Fakultät vom {news_article.pub_date} :loudspeaker:", embed=embed)
        except errors.NotFound:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(News(bot))
