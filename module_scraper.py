import asyncio
import re
from typing import List

import aiohttp
from bs4 import BeautifulSoup

import models
from models import Course, Module, Event, Support, Exam, Download, Contact


class Scraper:
    def __init__(self):
        self.base_url = 'https://www.fernuni-hagen.de'
        self.modules_scraped = {}

    async def scrape(self) -> None:
        with models.db.transaction() as txn:
            Module.delete().execute()
            Event.delete().execute()
            Support.delete().execute()
            Exam.delete().execute()
            Download.delete().execute()
            Contact.delete().execute()
            for course in Course.select():
                print(f"Get modules for {course.name}")
                await self.fetch_modules(course)
            modules = Module.select()
            for idx, module in enumerate(modules):
                print(f"{idx + 1}/{len(modules)} Get infos for {module.title}")
                await self.fetch_modules_infos(module)
            txn.commit()

    async def fetch_modules(self, course: Course) -> None:
        module_links = self.parse_index_page(await self.fetch(course.url))
        for module_link in module_links:
            Module.get_or_create(number=module_link["number"], title=module_link["title"], url=module_link["url"])

    async def fetch_modules_infos(self, module: Module) -> None:
        html = await self.fetch(module.url)
        self.parse_module_page(html, module)

    @staticmethod
    async def fetch(url: str) -> str:
        async with aiohttp.ClientSession() as session:
            req = await session.get(url, ssl=False)
            text = await req.read()
            return text

    def prepare_url(self, url: str) -> str:
        if re.search(r"^http(s)*://", url):
            return url
        elif re.search(r"^/", url):
            return self.base_url + url
        return self.base_url + "/" + url

    def parse_index_page(self, html: str) -> List:
        soup = BeautifulSoup(html, "html.parser")
        module_links = soup.findAll('a', string=re.compile(r'^[0-9]{5} '))
        return [{"title": module_link.get_text()[6:],
                 "number": int(re.search('^([0-9]+) ', module_link.get_text())[1]),
                 "url": self.prepare_url(module_link['href']).split("?")[0]}
                for module_link in module_links]

    def parse_module_page(self, html: str, module: Module) -> None:
        soup = BeautifulSoup(html, "html.parser")
        info = self.parse_info(soup)
        Module.update(ects=info["ects"], effort=info["effort"], duration=info["duration"], interval=info["interval"],
                      notes=info["notes"], requirements=info["requirements"]).where(
            Module.number == module.number).execute()

        for event in self.parse_events(soup):
            Event.create(name=event["name"], number=event["number"], url=event["url"], module=module)

        for support_item in self.parse_support(soup):
            Support.create(title=support_item["title"], city=support_item["city"], url=support_item["url"],
                           module=module)

        for exam in self.parse_exams(soup):
            Exam.create(name=exam["name"], type=exam["type"], requirements=exam["requirements"],
                        hard_requirements=exam["hard_requirements"], module=module)

        for download in self.parse_downloads(soup):
            models.Download.create(title=download["title"], url=download["url"], module=module)

        for contact in self.parse_contacts(soup):
            models.Contact.create(name=contact, module=module)

    def parse_info(self, soup):
        try:
            info_source = soup.find(summary='Modulinformationen')
        except:
            return None
        if info_source is None:
            return None

        return {
            "ects": self.get_info(info_source, 'ECTS'),
            "effort": self.get_info(info_source, 'Arbeitsaufwand'),
            "duration": self.get_info(info_source, 'Dauer des Moduls'),
            "interval": self.get_info(info_source, 'Häufigkeit des Moduls'),
            "notes": self.get_info(info_source, 'Anmerkung'),
            "requirements": self.get_info(info_source, 'Inhaltliche Voraussetzung')
        }

    def get_info(self, info_source, title):
        th = info_source.find('th', string=title)
        if th is not None:
            td = th.findNext('td')
            if td is not None:
                return td.get_text()
        return None

    def parse_events(self, soup):
        try:
            course_source = soup.find('h2', string=re.compile(r'Aktuelles Angebot')) \
                .findNext('div') \
                .findAll('a')
            return [{"name": re.sub('^Kurs [0-9]+ ', '', link.get_text()),
                     "number": re.sub('^0+', '', re.search('([^/]+)$', link['href'])[1]),
                     "url": self.prepare_url(link['href'])} for link in course_source]
        except:
            return []

    def parse_support(self, soup):
        try:
            support_source = soup.find('h2', string=re.compile(
                r'Mentorielle Betreuung an den Campusstandorten')).findNext('ul').findAll('li')
        except:
            support_source = []

        return [{"title": item.get_text(), "city": item.find('a').get_text(),
                 "url": self.prepare_url(item.find('a')['href'])} for item in support_source]

    @staticmethod
    def parse_exams(soup):
        try:
            exam_source = soup.find(summary='Prüfungsinformationen')
        except:
            return []
        stg = exam_source.findNext('th', colspan='2')
        exams = []
        while stg != None:
            exam = {
                "name": stg.get_text(),
                "type": stg.findNext('th', string='Art der Prüfungsleistung').findNext('td').get_text(),
                "requirements": stg.findNext('th', string='Voraussetzung').findNext('td').get_text(),
                # "weight": stg.findNext('th', string='Stellenwert der Note').findNext('td').get_text(),
                "hard_requirements": stg.findNext('th', string='Formale Voraussetzungen').findNext('td').get_text()
            }
            exams.append(exam)
            stg = stg.findNext('th', colspan='2')
        return exams

    def parse_downloads(self, soup):
        try:
            downloads = soup.find('h2', string=re.compile(r'Download')) \
                .findNext('ul', attrs={'class': 'pdfliste'}) \
                .findAll('li')
        except:
            downloads = []

        return [{"title": download.find('a').get_text(),
                 "url": self.prepare_url(download.find('a')['href'])}
                for download in downloads]

    @staticmethod
    def parse_contacts(soup):
        try:
            contacts = soup.find('h2', string=re.compile(
                r'Ansprechpersonen')).findNext('ul').findAll('h4')
        except:
            return []
        return [contact.get_text() for contact in contacts]


if __name__ == "__main__":
    scraper = Scraper()
    asyncio.run(scraper.scrape())
