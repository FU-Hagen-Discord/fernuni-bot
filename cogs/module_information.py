import json
import os
import re

import disnake
from disnake.ext import commands, tasks

import utils
from cogs.components.module_information.scraper import Scraper
from cogs.help import help, help_category, handle_error


class ModuleInformationNotFoundError(Exception):
    pass


class NoCourseChannelError(Exception):
    pass


class NoCourseOfStudyError(Exception):
    pass


"""
  Environment Variablen:
  DISCORD_MODULE_COURSE_FILE - Datei mit Studiengangsinformationen
  DISCORD_MODULE_DATA_FILE - In dieser Datei werden die gescrappten Daten gespeichert
"""


@help_category("moduleinformation", "Modulinformationen",
               "Mit diesen Kommandos kannst du dir Informationen zu einem Kurs/Modul anzeigen lassen. Die angezeigten Informationen sind abhängig von deinem Studiengang (also der Rolle die du gewählt hast).")
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

    async def execute_subcommand(self, ctx, arg_stg, subcommand=None):
        try:
            module = await self.find_module(ctx, arg_stg)
            await subcommand(ctx, module)
        except NoCourseOfStudyError:
            shorts = []
            for course_of_studies in self.data:
                shorts.append(f"`{course_of_studies['short']}`")
            await ctx.channel.send(
                f"Fehler! Wähle entweder eine Studiengangs-Rolle aus oder gebe ein Studiengangskürzel"
                f"nach dem Kommando an.\nMögliche Kürzel: {', '.join(shorts)}"
            )
            return None
        except NoCourseChannelError:
            return None
        except ModuleInformationNotFoundError as e:
            if e.args and e.args[0]:
                await ctx.channel.send(e.args[0])
            else:
                await ctx.channel.send("Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")

            return None

    async def get_stg_short(self, ctx, stg):
        if not stg:
            stg = await self.get_stg_short_from_role(ctx.author)
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

    async def find_module(self, ctx, arg_stg):
        short = await self.get_stg_short(ctx, arg_stg)
        number = self.number_of_channel(ctx.channel)
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
        except disnake.ext.commands.errors.CommandInvokeError:
            return None

    async def download_for(self, ctx, title, module):
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

        embed = disnake.Embed(title=title,
                              description=desc,
                              color=19607)
        await ctx.channel.send(embed=embed)

    async def handbook(self, ctx, module):
        try:
            await self.download_for(ctx, "Modulhandbuch", module)
        except ModuleInformationNotFoundError:
            raise ModuleInformationNotFoundError("Leider habe ich kein Modulhandbuch gefunden.")

    async def reading_sample(self, ctx, module):
        try:
            await self.download_for(ctx, "Leseprobe", module)
        except ModuleInformationNotFoundError:
            raise ModuleInformationNotFoundError("Leider habe ich keine Leseprobe gefunden.")

    async def info(self, ctx, module):
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
            desc += f"\nKurse: \n"
            for course in courses:
                desc += f"[{course['number']} - {course['name']}]({course['url']})\n"

        desc += self.stg_string_for_desc(module)
        embed = disnake.Embed(title=f"Modul {data['title']}",
                              description=desc,
                              color=19607)
        await ctx.channel.send(embed=embed)

    async def load(self, ctx, module):
        try:
            data = module['data']['page']['infos']['time']
            if not data:
                raise KeyError
        except KeyError:
            raise ModuleInformationNotFoundError

        time = re.sub(r': *(\r*\n*)*', ':\n', data)
        desc = f"{time}"
        desc += self.stg_string_for_desc(module)
        embed = disnake.Embed(title=f"Arbeitsaufwand",
                              description=desc,
                              color=19607)
        await ctx.channel.send(embed=embed)

    async def support(self, ctx, module):
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
        embed = disnake.Embed(title=f"Mentoriate ",
                              description=desc,
                              color=19607)
        await ctx.channel.send(embed=embed)

    async def exams(self, ctx, module):
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

        embed = disnake.Embed(title=f"Prüfungsinformationen",
                              description=desc,
                              color=19607)
        await ctx.channel.send(embed=embed)

    @help(
        category="moduleinformation",
        syntax="!module <command> <stg?>",
        parameters={
            "command": "Das Kommando, welches ausgeführt werden soll (aufwand, handbuch, info, leseprobe, mentoriate, prüfungen)",
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Ruft Modulinformation ab. "
    )
    @commands.group(name="module", aliases=["modul"], pass_context=True)
    async def cmd_module(self, ctx):
        if not ctx.invoked_subcommand:
            await self.cmd_module_info(ctx)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module update <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        mod=True,
        brief="Aktualisiert die Daten über die Module (manueller Aufruf im Normalfall nicht nötig). "
    )
    @cmd_module.command("update")
    @commands.check(utils.is_mod)
    async def cmd_module_update(self, ctx):
        await ctx.channel.send("Refreshing...")
        await self.refresh_data()

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module handbuch <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt den Link zum Modulhandbuch für dieses Modul an. "
    )
    @cmd_module.command("handbuch", aliases=["mhb", "hb", "modulhandbuch"])
    async def cmd_module_handbuch(self, ctx, arg_stg=None):
        await self.execute_subcommand(ctx, arg_stg, self.handbook)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module leseprobe <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt den Link zur Leseprobe für diesen Kurs an."
    )
    @cmd_module.command("probe", aliases=["leseprobe"])
    async def cmd_module_probe(self, ctx, arg_stg=None):
        await self.execute_subcommand(ctx, arg_stg, self.reading_sample)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module info <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt allgemeine Informationen zum Modul an."
    )
    @cmd_module.command("info")
    async def cmd_module_info(self, ctx, arg_stg=None):
        await self.execute_subcommand(ctx, arg_stg, self.info)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module aufwand <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt die Informationen zum zeitlichen Aufwand an. "
    )
    @cmd_module.command("aufwand", aliases=["workload", "load", "zeit", "arbeitzeit"])
    async def cmd_module_aufwand(self, ctx, arg_stg=None):
        await self.execute_subcommand(ctx, arg_stg, self.load)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module mentoriate <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt eine Liste der verfügbaren Mentoriate an."
    )
    @cmd_module.command("mentoriate", aliases=["mentoriat", "support"])
    async def cmd_module_mentoriate(self, ctx, arg_stg=None):
        await self.execute_subcommand(ctx, arg_stg, self.support)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module prüfungen <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs, für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt Informationen zur Prüfung an. "
    )
    @cmd_module.command("prüfungen", aliases=["exam", "exams", "prüfung"])
    async def cmd_module_pruefungen(self, ctx, arg_stg=None):
        await self.execute_subcommand(ctx, arg_stg, self.exams)

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
