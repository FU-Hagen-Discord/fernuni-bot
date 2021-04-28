from bs4 import BeautifulSoup
from urllib.request import urlopen
import re
import os
import json


class Scrapper:
    def __init__(self, filename):
        self.base_url = 'https://www.fernuni-hagen.de'
        self.courses_file = filename


    def scrap(self):
        courses_of_studies = self.load_courses_fo_studies()
        for course in courses_of_studies:
            self.fetch_module_infos_for_course_of_studies(course)
        return courses_of_studies


    def fetch_module_infos_for_course_of_studies(self, course):
        print(f"Fetching {course['name']}")
        url = course['url']
        html = self.fetch(url)
        modules = self.parse_index_page(html)
        for module in modules:
            print(f"Scrap {module['url']}")
            html = self.fetch(module['url'])
            module['page'] = self.parse_course_page(html, course)
        course['modules'] = modules


    def load_courses_fo_studies(self):
        group_file = open(self.courses_file, mode='r')
        return json.load(group_file)


    def fetch(self, url):
        response = urlopen(url)
        data = response.read()
        text = data.decode('utf-8')
        return text


    def prepare_url(self, url):
        if (re.search(r"^http(s)*://", url)):
            return url
        elif (re.search(r"^/", url)):
            return self.base_url + url
        return self.base_url + "/" + url


    def parse_index_page(self, html):
        soup = BeautifulSoup(html, "html.parser")
        modules_source = soup.findAll('a', text=re.compile(r'^[0-9]{5} '))
        modules = []
        for item in modules_source:
            module = {
                "title": item.get_text(),
                "number": re.sub('^0+','', re.search('^([0-9]+) ', item.get_text())[1]),
                "url": self.prepare_url(item['href'])
            }
            modules.append(module)
        return modules


    def parse_course_page(self, html, stg):
        soup = BeautifulSoup(html, "html.parser")
        module = {
            "title": self.parse_title(soup, stg),
            "infos": self.parse_infos(soup, stg),
            "courses": self.parse_courses(soup, stg),
            "support": self.parse_support(soup, stg),
            "exams": self.parse_exams(soup, stg),
            "downloads": self.parse_downloads(soup, stg),
            "persons": self.parse_persons(soup, stg)
        }
        return module


    def parse_title(self, soup, stg):
        title = re.sub(
            r" -.*FernUniversität in Hagen",
            "",
            soup.title.string,
            flags=re.S
        ).strip()
        return title


    def parse_infos(self, soup, stg):
        try:
        	info_source = soup.find(summary='Modulinformationen')
        except:
            return None
        infos = {
            "ects": info_source.find('th', text='ECTS').findNext('td').get_text(),
            "time": info_source.find('th', text='Arbeitsaufwand').findNext('td').get_text(),
            "duration": info_source.find('th', text='Dauer des Moduls').findNext('td').get_text(),
            "interval": info_source.find('th', text='Häufigkeit des Moduls').findNext('td').get_text(),
            "notes": info_source.find('th', text='Anmerkung').findNext('td').get_text(),
            "requirements": info_source.find('th', text='Inhaltliche Voraussetzung').findNext('td').get_text()
        }
        return infos


    def parse_courses(self, soup, stg):
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
                "number": re.sub('^0+','', re.search('([^/]+)$', link['href'])[1]),
                "url": self.prepare_url(link['href'])
            }
            courses.append(course)
        return courses


    def parse_support(self, soup, stg):
        try:
            support_source = soup.find('h2', text=re.compile(
                r'Mentorielle Betreuung in Regional- und Studienzentren')).findNext('div').findAll('li')
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


    def parse_exams(self, soup, _):
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
            download_source = soup.find('h2', text=re.compile(r'Download')) \
                .findNext('ul', class_="pdfliste") \
                .findAll('li', class_= re.compile(stg['short']))
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


    def parse_persons(self, soup, stg):
        try:
            person_source = soup.find('h2', text=re.compile(
                r'Ansprechpersonen')).findNext('ul').findAll('h4')
        except:
            return None
        persons = []
        for item in person_source:
            persons.append(item.get_text())
        return persons