import utils
from help.help import help, help_category
from module_information.scrapper import Scrapper

import json
import os
import re
import discord
from discord.ext import commands, tasks

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
            scrapper = Scrapper(self.courses_file)
            print("Refresh started")
            data = await scrapper.scrap()
            self.data = data
            self.save_data()
            print("Refresh finished")
        except:
            print("Can't refresh Data")
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
        except:
            self.data = {}

    def number_of_channel(self, channel):
        number = re.search(r"^([0-9]*)-", channel.name)[1]
        return number

    def stg_string_for_desc(self, result):
        desc = f"\n*({result['stg']})*"
        desc += ("\n*Es wurden keine Informationen für deinen Studiengang gefunden,"
                 "daher wird der erste Eintrag angezeigt*"
                 if 'notfound' in result else "")
        return desc

    async def get_stg(self, ctx, arg_stg):
        if not arg_stg:
            arg_stg = await self.get_stg_from_role(ctx.author)
        if not arg_stg:
            shorts = []
            for course_of_studies in self.data:
                shorts.append(f"`{course_of_studies['short']}`")
            await ctx.channel.send(
                f"Fehler! Wähle entweder eine Studiengangs-Rolle aus oder gebe ein Studiengangskürzel nach dem Kommando an.\nMögliche Kürzel: {', '.join(shorts)}")
        return arg_stg

    async def find_module(self, number, stg):
        valid_modules = []
        for course_of_studies in self.data:
            for module in course_of_studies['modules']:
                for course in module['page']['courses']:
                    cn = re.sub(r'^0+', '', course['number'])
                    n = re.sub(r'^0+', '', number)
                    if n == cn:
                        valid_modules.append(
                            {"stg": course_of_studies['name'], "short": course_of_studies['short'], "module": module})
        for module in valid_modules:
            if module['short'] == stg:
                return module

        if (len(valid_modules) == 0):
            return None
        module = valid_modules[0]
        module['notfound'] = True
        return module

    async def get_stg_from_role(self, user):
        for course_of_studies in self.data:
            if 'role' in course_of_studies:
                for r in user.roles:
                    if str(r.id) == course_of_studies['role']:
                        return course_of_studies['short']
        return None

    async def download_for(self, text, channel, stg):
        number = self.number_of_channel(channel)
        result = await self.find_module(number, stg)
        module = result['module']
        desc = ""
        found = False
        for download in module['page']['downloads']:
            if re.search(text, download['title']):
                found = True
                desc += f"[{download['title']}]({download['url']})\n"
        desc += self.stg_string_for_desc(result)
        return desc if found else None

    async def handbook(self, channel, stg):
        desc = await self.download_for(r"Modulhandbuch", channel, stg)
        if desc is None:
            await channel.send("Leider habe ich kein Modulhandbuch gefunden")
            return
        embed = discord.Embed(title="Modulehandbuch",
                              description=desc,
                              color=19607)
        await channel.send(embed=embed)

    async def reading_sample(self, channel, stg):
        desc = await self.download_for(r"Leseprobe", channel, stg)
        if desc is None:
            await channel.send("Leider habe ich keine Leseprobe gefunden")
            return
        embed = discord.Embed(title="Leseprobe",
                              description=desc,
                              color=19607)
        await channel.send(embed=embed)

    async def info(self, channel, stg):
        number = self.number_of_channel(channel)
        result = await self.find_module(number, stg)
        if not result:
            await channel.send("Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")
        module = result['module']

        infos = module['page']['infos']
        desc = (f"Wie viele Credits bekomme ich? **{infos['ects']} ECTS**\n"
                f"Wie lange geht das Modul? **{infos['duration']}**\n"
                f"Wie oft wird das Modul angeboten? **{infos['interval']}**\n"
                )

        if len(infos['requirements']) > 0 and infos['requirements'] != 'keine':
            desc += f"\nInhaltliche Voraussetzungen: \n{infos['requirements']}\n"

        if len(infos['notes']) > 0 and infos['notes'] != '-':
            desc += f"\nAnmerkungen: \n\n{infos['notes']}\n"

        if len(module['page']['persons']) > 0:
            desc += f"\nAnsprechparnter: \n"
            desc += ', '.join(module['page']['persons']) + "\n"

        if len(module['page']['courses']) > 0:
            desc += f"\nKurse: \n"
            for course in module['page']['courses']:
                desc += f"[{course['number']} - {course['name']}]({course['url']})\n"

        if desc is None:
            await channel.send("Leider habe ich keine Leseprobe gefunden")
            return
        desc += self.stg_string_for_desc(result)
        embed = discord.Embed(title=f"Modul {module['title']}",
                              description=desc,
                              color=19607)
        await channel.send(embed=embed)

    async def load(self, channel, stg):
        number = self.number_of_channel(channel)
        result = await self.find_module(number, stg)
        if not result:
            await channel.send("Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")

        module = result['module']
        infos = module['page']['infos']
        time = re.sub(r': *(\r*\n*)*', ':\n', infos['time'])
        desc = f"{time}"
        desc += self.stg_string_for_desc(result)
        embed = discord.Embed(title=f"Arbeitsaufwand",
                              description=desc,
                              color=19607)
        await channel.send(embed=embed)

    async def support(self, channel, stg):
        number = self.number_of_channel(channel)
        result = await self.find_module(number, stg)
        if not result:
            await channel.send("Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")
        module = result['module']
        desc = ""
        if not module['page']['support']:
            await channel.send(f"Leider habe ich keine Mentoriate gefunden.")
            return
        for support in module['page']['support']:
            desc += f"[{support['title']}]({support['url']})\n"
        desc += self.stg_string_for_desc(result)
        embed = discord.Embed(title=f"Mentoriate ",
                              description=desc,
                              color=19607)
        await channel.send(embed=embed)

    async def exams(self, channel, stg):
        number = self.number_of_channel(channel)
        result = await self.find_module(number, stg)
        if not result:
            await channel.send("Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")
        module = result['module']
        desc = ""
        for exam in module['page']['exams']:
            desc += f"**{exam['name']}**\n{exam['type']}\n"
            if len(exam['weight']) > 0 and exam['weight'] != '-':
                desc += f"Gewichtung: **{exam['weight']}**\n"
            desc += "\n"
            if len(exam['requirements']) > 0 and exam['requirements'] != 'keine':
                desc += f"Inhaltliche Voraussetzungen: \n{exam['requirements']}\n\n"
            if len(exam['hard_requirements']) > 0 and exam['hard_requirements'] != 'keine':
                desc += f"Formale Voraussetzungen: \n{exam['hard_requirements']}\n\n"
        # desc += self.stg_string_for_desc(result)
        embed = discord.Embed(title=f"Prüfungsinformationen",
                              description=desc,
                              color=19607)
        await channel.send(embed=embed)

    @help(
        category="moduleinformation",
        syntax="!module <command> <stg?>",
        parameters={
            "command": "Das Kommando welches ausgeführt werden soll (aufwand, handbuch, info, leseprobe, mentoriate, prüfungen)",
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Ruft Modulinformation ab. "
    )
    @commands.group(name="module", aliases=["modul"], pass_context=True)
    async def cmd_module(self, ctx):
        if not ctx.invoked_subcommand:
            await self.help(ctx.channel)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module update <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
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
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt den Link zum Modulhandbuch für dieses Modul an. "
    )
    @cmd_module.command("handbuch", aliases=["mhb", "hb", "modulhandbuch"])
    async def cmd_module_handbuch(self, ctx, arg_stg=None):
        stg = await self.get_stg(ctx, arg_stg)
        if not stg:
            return
        await self.handbook(ctx.channel, stg)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module leseprobe <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt den Link zur Leseprobe für diesen Kurs an. "
    )
    @cmd_module.command("probe", aliases=["leseprobe"])
    async def cmd_module_probe(self, ctx, arg_stg=None):
        stg = await self.get_stg(ctx, arg_stg)
        if not stg:
            return
        await self.reading_sample(ctx.channel, stg)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module info <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt allgeimeine Informationen zum Modul an. "
    )
    @cmd_module.command("info")
    async def cmd_module_info(self, ctx, arg_stg=None):
        stg = await self.get_stg(ctx, arg_stg)
        if not stg:
            return
        await self.info(ctx.channel, stg)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module aufwand <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt die Informationen zum zeitlichen Aufwand an. "
    )
    @cmd_module.command("aufwand", aliases=["workload", "load", "zeit", "arbeitzeit"])
    async def cmd_module_aufwand(self, ctx, arg_stg=None):
        stg = await self.get_stg(ctx, arg_stg)
        if not stg:
            return
        await self.load(ctx.channel, stg)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module mentoriate <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt eine Liste der verfügbaren Mentoriate an. "
    )
    @cmd_module.command("mentoriate", aliases=["mentoriat", "support"])
    async def cmd_module_mentoriate(self, ctx, arg_stg=None):
        stg = await self.get_stg(ctx, arg_stg)
        if not stg:
            return
        await self.support(ctx.channel, stg)

    @help(
        command_group="module",
        category="moduleinformation",
        syntax="!module prüfungen <stg?>",
        parameters={
            "stg": "*(optional)* Kürzel des Studiengangs für den die Informationen angezeigt werden sollen (bainf, bamath, bscmatse, bawiinf, mscma, mscinf, mawiinf, mscprinf)"
        },
        brief="Zeigt Informationen zur Prüfung an. "
    )
    @cmd_module.command("prüfungen", aliases=["exam", "exams", "prüfung"])
    async def cmd_module_pruefungen(self, ctx, arg_stg=None):
        stg = await self.get_stg(ctx, arg_stg)
        if not stg:
            return
        await self.exams(ctx.channel, stg)
