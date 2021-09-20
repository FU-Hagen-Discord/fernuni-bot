import json
import re

import aiohttp
from bs4 import BeautifulSoup


class Scraper:
    def __init__(self, filename):
        self.base_url = 'https://www.fernuni-hagen.de'
        self.courses_file = filename

    async def scrape(self):
        courses_of_studies = self.load_courses_of_studies()
        for course in courses_of_studies:
            await self.fetch_module_infos_for_course_of_studies(course)
        return courses_of_studies

    async def fetch_module_infos_for_course_of_studies(self, course):
        url = course['url']
        html = await self.fetch(url)
        modules = self.parse_index_page(html)
        for module in modules:
            html = await self.fetch(module['url'])
            module['page'] = self.parse_course_page(html, course)
        course['modules'] = modules

    def load_courses_of_studies(self):
        group_file = open(self.courses_file, mode='r')
        return json.load(group_file)

    async def fetch(self, url):
        #print (f"Fetching {url}")
        sess = aiohttp.ClientSession()
        req = await sess.get(url)
        text = await req.read()
        await sess.close()
        return text

    def prepare_url(self, url):
        if re.search(r"^http(s)*://", url):
            return url
        elif re.search(r"^/", url):
            return self.base_url + url
        return self.base_url + "/" + url

    def parse_index_page(self, html):
        soup = BeautifulSoup(html, "html.parser")
        modules_source = soup.findAll('a', text=re.compile(r'^[0-9]{5} '))
        modules = []
        for item in modules_source:
            module = {
                "title": item.get_text(),
                "number": re.sub('^0+', '', re.search('^([0-9]+) ', item.get_text())[1]),
                "url": self.prepare_url(item['href'])
            }
            modules.append(module)
        return modules

    def parse_course_page(self, html, stg):
        soup = BeautifulSoup(html, "html.parser")
        module = {
            "title": self.parse_title(soup),
            "infos": self.parse_infos(soup),
            "courses": self.parse_courses(soup),
            "support": self.parse_support(soup),
            "exams": self.parse_exams(soup),
            "downloads": self.parse_downloads(soup, stg),
            "persons": self.parse_persons(soup)
        }
        return module

    def parse_title(self, soup):
        title = re.sub(
            r" -.*FernUniversität in Hagen",
            "",
            soup.title.string,
            flags=re.S
        ).strip()
        return title

    def parse_infos(self, soup):
        try:
            info_source = soup.find(summary='Modulinformationen')
        except:
            return None

        infos = {
            "ects": self.get_info(info_source, 'ECTS'),
            "time": self.get_info(info_source, 'Arbeitsaufwand'),
            "duration": self.get_info(info_source, 'Dauer des Moduls'),
            "interval": self.get_info(info_source, 'Häufigkeit des Moduls'),
            "notes": self.get_info(info_source, 'Anmerkung'),
            "requirements": self.get_info(info_source, 'Inhaltliche Voraussetzung')
        }

        return infos

    def get_info(self, info_source, title):
        th = info_source.find('th', text=title)
        if th is not None:
            td = th.findNext('td')
            if td is not None:
                return td.get_text()
        return None

    def parse_courses(self, soup):
        try:
            course_source = soup.find('h2', text=re.compile(r'Aktuelles Angebot')) \
                .findNext('div') \
                .findAll('a')
        except:
            return None
        courses = []
        for link in course_source:
            course = {
                "name": re.sub('^Kurs [0-9]+ ', '', link.get_text()),
                "number": re.sub('^0+', '', re.search('([^/]+)$', link['href'])[1]),
                "url": self.prepare_url(link['href'])
            }
            courses.append(course)
        return courses

    def parse_support(self, soup):
        try:
            support_source = soup.find('h2', text=re.compile(
                r'Mentorielle Betreuung in Regionalzentren')).findNext('div').findAll('li')
        except:
            return None

        supports = None
        if support_source:
            supports = []
            for item in support_source:
                support = {
                    "title": item.get_text(),
                    "city": item.find('a').get_text(),
                    "url": self.prepare_url(item.find('a')['href'])
                }
                supports.append(support)
        return supports

    def parse_exams(self, soup):
        try:
            exam_source = soup.find(summary='Prüfungsinformationen')
        except:
            return None
        stg = exam_source.findNext('th', colspan='2')
        exams = []
        while stg != None:
            exam = {
                "name": stg.get_text(),
                "type": stg.findNext('th', text='Art der Prüfungsleistung').findNext('td').get_text(),
                "requirements": stg.findNext('th', text='Voraussetzung').findNext('td').get_text(),
                "weight": stg.findNext('th', text='Stellenwert der Note').findNext('td').get_text(),
                "hard_requirements": stg.findNext('th', text='Formale Voraussetzungen').findNext('td').get_text()
            }
            exams.append(exam)
            stg = stg.findNext('th', colspan='2')
        return exams

    def parse_downloads(self, soup, stg):
        try:
            source1 = soup.find('h2', text=re.compile(r'Download')) \
                .findNext('ul', attrs={'class': 'pdfliste'}) \
                .findAll('li', attrs={'class': None})
            source2 = soup.find('h2', text=re.compile(r'Download')) \
                .findNext('ul', attrs={'class': 'pdfliste'}) \
                .findAll('li', attrs={'class': re.compile(stg['short'])})

            download_source = [*source1, *source2]

        except:
            return None

        downloads = None
        if download_source:
            downloads = []
            for item in download_source:
                download = {
                    "title": item.find('a').get_text(),
                    "url": self.prepare_url(item.find('a')['href'])
                }
                downloads.append(download)
        return downloads

    def parse_persons(self, soup):
        try:
            person_source = soup.find('h2', text=re.compile(
                r'Ansprechpersonen')).findNext('ul').findAll('h4')
        except:
            return None
        persons = []
        for item in person_source:
            persons.append(item.get_text())
        return persons
