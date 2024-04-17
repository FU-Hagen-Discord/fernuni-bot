import enum
import json
import os
import re

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from extensions.components.module_information.scraper import Scraper


class ModuleInformationNotFoundError(Exception):
    pass


class NoCourseChannelError(Exception):
    pass


class NoCourseOfStudyError(Exception):
    pass


class Topics(enum.Enum):
    info = 1
    handbuch = 2
    leseprobe = 3
    aufwand = 4
    mentoriate = 5
    pruefungen = 6


class CoursesOfStudy(enum.Enum):
    bainf = "bainf"
    bamath = "bamath"
    bscmatse = "bscmatse"
    bawiinf = "bawiinf"
    mscma = "mscma"
    mscinf = "mscinf"
    mawiinf = "mawiinf"
    mscprinf = "mscprinf"
    mscds = "mscds"


"""
  Environment Variablen:
  DISCORD_MODULE_COURSE_FILE - Datei mit Studiengangsinformationen
  DISCORD_MODULE_DATA_FILE - In dieser Datei werden die gescrappten Daten gespeichert
"""


class ModuleInformation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = []
        self.roles_channel_id = int(os.getenv("DISCORD_ROLLEN_CHANNEL"))
        self.data_file = os.getenv("DISCORD_MODULE_DATA_FILE")
        self.courses_file = os.getenv("DISCORD_MODULE_COURSE_FILE")
        self.load_data()
        self.update_loop.start()

    @tasks.loop(hours=24)
    async def update_loop(self):
        await self.refresh_data()

    async def refresh_data(self):
        try:
            scrapper = Scraper(self.courses_file)
            print("Refresh started")
            data = await scrapper.scrape()
            self.data = data
            self.save_data()
            print("Refresh finished")
        except:
            print("Can't refresh data")
            pass

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()

    def save_data(self):
        data_file = open(self.data_file, mode='w')
        json.dump(self.data, data_file)

    def load_data(self):
        try:
            data_file = open(self.data_file, mode='r')
            self.data = json.load(data_file)
        except FileNotFoundError:
            self.data = {}

    def number_of_channel(self, channel):
        try:
            number = re.search(r"^([0-9]*)-", channel.name)[1]
            return number
        except TypeError:
            raise NoCourseChannelError

    def stg_string_for_desc(self, module):
        desc = f"\n*({module['stg']})*"
        desc += ("\n*Es wurden keine Informationen für deinen Studiengang gefunden,"
                 "daher wird der erste Eintrag angezeigt*"
                 if 'notfound' in module else "")
        return desc

    async def execute_subcommand(self, interaction: Interaction, arg_stg, subcommand=None):
        try:
            module = await self.find_module(interaction.user, interaction.channel, arg_stg)
            embed = await subcommand(module)
            await interaction.edit_original_response(embed=embed)
        except NoCourseOfStudyError:
            shorts = []
            for course_of_studies in self.data:
                shorts.append(f"`{course_of_studies['short']}`")
            await interaction.edit_original_response(content=
                                                     f"Fehler! Wähle entweder eine Studiengangs-Rolle aus oder gebe ein Studiengangskürzel "
                                                     f"nach dem Kommando an.\nMögliche Kürzel: {', '.join(shorts)}"
                                                     )
            return None
        except NoCourseChannelError:
            return None
        except ModuleInformationNotFoundError as e:
            if e.args and e.args[0]:
                await interaction.edit_original_response(content=e.args[0])
            else:
                await interaction.edit_original_response(
                    content="Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")

            return None

    async def get_stg_short(self, user, stg):
        if not stg:
            stg = await self.get_stg_short_from_role(user)
        if not stg:
            raise NoCourseOfStudyError
        return stg

    async def get_valid_modules_for_course_number(self, number):
        valid_modules = []
        try:
            for course_of_studies in self.data:
                if course_of_studies['modules'] is not None:
                    for module in course_of_studies['modules']:
                        if module['page']['courses'] is not None:
                            for course in module['page']['courses']:
                                cn = re.sub(r'^0+', '', course['number'])
                                n = re.sub(r'^0+', '', number)
                                if n == cn:
                                    valid_modules.append({
                                        "stg": course_of_studies['name'],
                                        "short": course_of_studies['short'],
                                        "data": module
                                    })
                        else:
                            print(f"[ModuleInformation] {module['number']} is an invalid Module")
            return valid_modules
        except:
            return []

    async def find_module(self, user, channel, arg_stg):
        short = await self.get_stg_short(user, arg_stg)
        number = self.number_of_channel(channel)
        valid_modules = await self.get_valid_modules_for_course_number(number)

        if len(valid_modules) == 0:
            raise ModuleInformationNotFoundError

        for module in valid_modules:
            if module.get('short') == short:
                return module

        module = valid_modules[0]
        module['notfound'] = True
        return module

    async def get_stg_short_from_role(self, user):
        try:
            for course_of_studies in self.data:
                if 'role' in course_of_studies:
                    for r in user.roles:
                        if str(r.id) == course_of_studies['role']:
                            return course_of_studies['short']
            return None
        except discord.ext.commands.errors.CommandInvokeError:
            return None

    async def download_for(self, title, module):
        try:
            data = module['data']['page']['downloads']
            if not data:
                raise KeyError
        except KeyError:
            raise ModuleInformationNotFoundError

        desc = ""
        found = False
        for download in data:
            if re.search(title, download['title']):
                found = True
                desc += f"[{download['title']}]({download['url']})\n"
        desc += self.stg_string_for_desc(module)
        if not found:
            raise ModuleInformationNotFoundError

        return discord.Embed(title=title,
                             description=desc,
                             color=19607)

    async def handbook(self, module):
        try:
            return await self.download_for("Modulhandbuch", module)
        except ModuleInformationNotFoundError:
            raise ModuleInformationNotFoundError("Leider habe ich kein Modulhandbuch gefunden.")

    async def reading_sample(self, module):
        try:
            return await self.download_for("Leseprobe", module)
        except ModuleInformationNotFoundError:
            raise ModuleInformationNotFoundError("Leider habe ich keine Leseprobe gefunden.")

    async def info(self, module):
        try:
            data = module['data']
            info = data['page']['infos']
            if not data or not info:
                raise KeyError
        except KeyError:
            raise ModuleInformationNotFoundError

        desc = (f"Wie viele Credits bekomme ich? **{info['ects']} ECTS**\n"
                f"Wie lange geht das Modul? **{info['duration']}**\n"
                f"Wie oft wird das Modul angeboten? **{info['interval']}**\n"
                )

        if (requirements := info.get('requirements')) and len(requirements) > 0 and requirements != 'keine':
            desc += f"\nInhaltliche Voraussetzungen: \n{requirements}\n"

        if (notes := info.get('notes')) and len(notes) > 0 and notes != '-':
            desc += f"\nAnmerkungen: \n\n{notes}\n"

        if (persons := data['page'].get('persons')) and len(persons) > 0:
            desc += f"\nAnsprechparnter: \n"
            desc += ', '.join(persons) + "\n"

        if (courses := data['page'].get('courses')) and len(courses) > 0:
            desc += f"\nModul in der VU: \n"
            for course in courses:
                desc += f"[{course['name']}]({course['url']})\n"

        desc += self.stg_string_for_desc(module)
        return discord.Embed(title=f"Modul {data['title']}",
                             description=desc,
                             color=19607)

    async def load(self, module):
        try:
            data = module['data']['page']['infos']['time']
            if not data:
                raise KeyError
        except KeyError:
            raise ModuleInformationNotFoundError

        time = re.sub(r': *(\r*\n*)*', ':\n', data)
        desc = f"{time}"
        desc += self.stg_string_for_desc(module)
        return discord.Embed(title=f"Arbeitsaufwand",
                             description=desc,
                             color=19607)

    async def support(self, module):
        try:
            data = module['data']['page']['support']
            if not data:
                raise KeyError
        except KeyError:
            raise ModuleInformationNotFoundError(f"Leider habe ich keine Mentoriate gefunden.")

        desc = ""
        for support in data:
            desc += f"[{support['title']}]({support['url']})\n"
        desc += self.stg_string_for_desc(module)
        return discord.Embed(title=f"Mentoriate ",
                             description=desc,
                             color=19607)

    async def exams(self, module):
        try:
            data = module['data']['page']['exams']
            if not data:
                raise KeyError
        except KeyError:
            raise ModuleInformationNotFoundError(f"Leider habe ich keine Prüfungsinformationen gefunden.")

        desc = ""
        for exam in data:
            desc += f"**{exam['name']}**\n{exam['type']}\n"
            if (weight := exam.get('weight')) and len(weight) > 0 and weight != '-':
                desc += f"Gewichtung: **{weight}**\n"
            desc += "\n"

            if (requirements := exam.get('requirements')) and len(requirements) > 0 and requirements != 'keine':
                desc += f"Inhaltliche Voraussetzungen: \n{requirements}\n\n"

            if (hard_requirements := exam.get('hard_requirements')) and len(hard_requirements) > 0 \
                    and hard_requirements != 'keine':
                desc += f"Formale Voraussetzungen: \n{hard_requirements}\n\n"
        # desc += self.stg_string_for_desc(module)

        return discord.Embed(title=f"Prüfungsinformationen",
                             description=desc,
                             color=19607)

    @app_commands.command(name="module",
                          description="Erhalte Informationen zu einem Kurs/Modul, abhängig von deinem Studiengang")
    @app_commands.describe(public="Zeige die Ausgabe des Commands öffentlich, für alle Mitglieder sichtbar.",
                           topic="Welche speziellen Informationen interessieren dich?",
                           stg="Der Studiengang, für den die Informationen angezeigt werden sollen.")
    async def cmd_module(self, interaction: Interaction, public: bool, topic: Topics = None,
                         stg: CoursesOfStudy = None):
        await interaction.response.defer(ephemeral=not public)

        if topic == Topics.handbuch:
            await self.execute_subcommand(interaction, stg, self.handbook)
        elif topic == Topics.leseprobe:
            await self.execute_subcommand(interaction, stg, self.reading_sample)
        elif topic == Topics.aufwand:
            await self.execute_subcommand(interaction, stg, self.load)
        elif topic == Topics.mentoriate:
            await self.execute_subcommand(interaction, stg, self.support)
        elif topic == Topics.pruefungen:
            await self.execute_subcommand(interaction, stg, self.exams)
        else:
            await self.execute_subcommand(interaction, stg, self.info)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModuleInformation(bot))
