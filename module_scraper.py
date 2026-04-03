import logging
import re
from typing import List
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

import models
from models import Course, Module, ModuleCourse

_log = logging.getLogger("discord.boty.module_scraper")


class Scraper:
    def __init__(self):
        self.base_url = 'https://www.fernuni-hagen.de'

    async def scrape(self) -> None:
        async with aiohttp.ClientSession() as session:
            with models.db.transaction() as txn:
                ModuleCourse.delete().execute()
                Module.delete().execute()
                courses = list(Course.select())
                _log.info("Starting module scrape for %d courses", len(courses))
                for course in courses:
                    _log.debug("Scraping module index for course: %s", course.name)
                    await self.fetch_modules(session, course)
                txn.commit()
                _log.info("Module scrape finished")

    async def fetch_modules(self, session: aiohttp.ClientSession, course: Course) -> None:
        async with session.get(course.url) as req:
            module_links = self.parse_index_page(await req.read())
            for module_link in module_links:
                module, _ = Module.get_or_create(
                    number=module_link["number"],
                    defaults={"title": module_link["title"], "url": module_link["url"]}
                )
                ModuleCourse.get_or_create(module=module, course=course)

    def parse_index_page(self, html: bytes) -> List:
        soup = BeautifulSoup(html, "html.parser")
        module_links = [
            link for link in soup.find_all('a')
            if link.get_text() and re.match(r'^\d{5} ', link.get_text())
        ]
        return [{"title": module_link.get_text()[6:],
                 "number": int(re.search(r'^(\d+) ', module_link.get_text())[1]),
                 "url": urljoin(self.base_url, module_link['href']).split("?")[0]}
                for module_link in module_links]
