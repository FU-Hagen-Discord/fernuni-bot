import enum
import re

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from models import Module, Download


class ModuleInformationNotFoundError(Exception):
    pass


class NoCourseChannelError(Exception):
    pass


class Topics(enum.Enum):
    info = 1
    handbuch = 2
    leseprobe = 3
    aufwand = 4
    mentoriate = 5
    pruefungen = 6


class ModuleInformation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.update_loop.start()

    @tasks.loop(hours=24)
    # Replace with loop that checks if updates happened or not and send a notification in case it did not.
    async def update_loop(self):
        pass
        # await self.refresh_data()

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()

    @staticmethod
    async def find_module(channel, number):
        if not number:
            try:
                number = re.search(r"^([0-9]*)-", channel.name)[1]
            except TypeError:
                raise NoCourseChannelError

        # At this point we can be sure to have a number. Either passed in from the user as argument or from the channel name
        if module := Module.get_or_none(Module.number == number):
            return module
        else:
            raise ModuleInformationNotFoundError(f"Zum Modul mit der Nummer {number} konnte ich keine Informationen "
                                                 f"finden. Bitte geh sicher, dass dies ein gültiges Modul ist. "
                                                 f"Ansonsten schreibe mir eine Direktnachricht und ich leite sie "
                                                 f"weiter an das Mod-Team.")

    @staticmethod
    async def download_for(title, module):
        desc = ""
        found = False
        for download in module.downloads.where(Download.title.contains(title)):
            found = True
            desc += f"[{download.title}]({download.url})\n"
        if not found:
            raise ModuleInformationNotFoundError

        return discord.Embed(title=title,
                             description=desc,
                             color=19607, url=module.url)

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

    @staticmethod
    async def info(module):
        desc = (f"Wie viele Credits bekomme ich? **{module.ects} ECTS**\n"
                f"Wie lange geht das Modul? **{module.duration}**\n"
                f"Wie oft wird das Modul angeboten? **{module.interval}**\n"
                )

        if (requirements := module.requirements) and len(requirements) > 0 and requirements != 'keine':
            desc += f"\nInhaltliche Voraussetzungen: \n{requirements}\n"

        if (notes := module.notes) and len(notes) > 0 and notes != '-':
            desc += f"\nAnmerkungen: \n\n{notes}\n"

        if (contacts := module.contacts) and len(contacts) > 0:
            desc += f"\nAnsprechparnter: \n"
            desc += ', '.join([contact.name for contact in contacts]) + "\n"

        if (events := module.events) and len(events) > 0:
            desc += f"\nAktuelles Angebot in der VU: \n"
            for event in events:
                desc += f"[{event.name}]({event.url})\n"

        return discord.Embed(title=f"Modul {module.title}",
                             description=desc,
                             color=19607, url=module.url)

    @staticmethod
    async def effort(module):
        if not module.effort or len(module.effort) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit nichts über den Aufwand des Moduls {module.number}-{module.title} sagen.")

        effort = re.sub(r': *(\r*\n*)*', ':\n', module.effort)
        return discord.Embed(title=f"Arbeitsaufwand",
                             description=f"{effort}",
                             color=19607, url=module.url)

    @staticmethod
    async def support(module):
        if len(module.support) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit keine Mentoriate für das Modul {module.number}-{module.title} finden.")

        desc = ""
        for support in module.support:
            desc += f"[{support.title}]({support.url})\n"
        return discord.Embed(title=f"Mentoriate ",
                             description=desc,
                             color=19607, url=module.url)

    @staticmethod
    async def exams(module):
        if len(module.exams) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit keine Prüfungsinformationen für das Modul {module.number}-{module.title} finden.")

        desc = ""
        for exam in module.exams:
            desc += f"**{exam.name}**\n{exam.type}\n"
            if exam.weight and len(exam.weight) > 0 and exam.weight != '-':
                desc += f"Gewichtung: **{exam.weight}**\n"
            desc += "\n"

            if exam.requirements and len(exam.requirements) > 0 and exam.requirements != 'keine':
                desc += f"Inhaltliche Voraussetzungen: \n{exam.requirements}\n\n"

            if exam.hard_requirements and len(exam.hard_requirements) > 0 \
                    and exam.hard_requirements != 'keine':
                desc += f"Formale Voraussetzungen: \n{exam.hard_requirements}\n\n"

        return discord.Embed(title=f"Prüfungsinformationen",
                             description=desc,
                             color=19607, url=module.url)

    async def get_embed(self, module: Module, topic: Topics):
        if topic == Topics.handbuch:
            return await self.handbook(module)
        elif topic == Topics.leseprobe:
            return await self.reading_sample(module)
        elif topic == Topics.aufwand:
            return await self.effort(module)
        elif topic == Topics.mentoriate:
            return await self.support(module)
        elif topic == Topics.pruefungen:
            return await self.exams(module)
        return await self.info(module)

    @app_commands.command(name="module",
                          description="Erhalte die Modulinformationen von der Uniwebseite.")
    @app_commands.describe(public="Sichtbarkeit der Ausgabe: für alle Mitglieder oder nur für dich.",
                           topic="Möchtest du eine bestimmte Rubrik abrufen?",
                           module_nr="Nummer des Moduls, das dich interessiert. (In einem Moduilkanal optional).")
    async def cmd_module(self, interaction: Interaction, public: bool, topic: Topics = None, module_nr: int = None):
        await interaction.response.defer(ephemeral=not public)

        try:
            module = await self.find_module(interaction.channel, module_nr)
            embed = await self.get_embed(module, topic)
            await interaction.edit_original_response(embed=embed)
        except NoCourseChannelError:
            await interaction.edit_original_response(
                content="Ich konnte keine Modulnummer finden. Bitte gib entweder die Modulnummer direkt an, "
                        "oder verwende dieses Kommando in einem Modulkanal.")
        except ModuleInformationNotFoundError as e:
            if e.args and e.args[0]:
                await interaction.edit_original_response(content=e.args[0])
            else:
                await interaction.edit_original_response(
                    content="Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModuleInformation(bot))
