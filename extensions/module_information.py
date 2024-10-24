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
        downloads = [f"- [{download.title}]({download.url})" for download in module.downloads.where(Download.title.contains(title))]
        if len(downloads) == 0:
            raise ModuleInformationNotFoundError

        return discord.Embed(title=f"{title} {module.title}",
                             description="\n".join(downloads),
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
        embed = discord.Embed(title=f"Modul {module.title}",
                             color=19607, url=module.url)
        embed.add_field(name="Wie viele Credits bekomme ich?", value=f"{module.ects} ECTS", inline=False)
        embed.add_field(name="Wie lange geht das Modul?", value=module.duration, inline=False)
        embed.add_field(name="Wie oft wird das Modul angeboten?", value=module.interval, inline=False)
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        if (requirements := module.requirements) and len(requirements) > 0 and requirements not in  ['keine', "-"]:
            embed.add_field(name="Inhaltliche Voraussetzungen", value=requirements, inline=False)

        if (notes := module.notes) and len(notes) > 0 and notes != '-':
            embed.add_field(name="Anmerkunden", value=notes, inline=False)

        if (contacts := module.contacts) and len(contacts) > 0:
            embed.add_field(name="Ansprechpartner", value=', '.join([f"- {contact.name}" for contact in contacts]), inline=False)

        if (events := module.events) and len(events) > 0:
            embed.add_field(name="Aktuelles Angebot in der VU", value="\n".join([f"- [{event.name}]({event.url})" for event in events]), inline=False)

        return embed

    @staticmethod
    async def effort(module):
        if not module.effort or len(module.effort) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit nichts über den Aufwand des Moduls {module.number}-{module.title} sagen.")

        effort = re.sub(r': *(\r*\n*)*', ':\n', module.effort)
        return discord.Embed(title=f"Arbeitsaufwand {module.title}",
                             description=f"{effort}",
                             color=19607, url=module.url)

    @staticmethod
    async def support(module):
        if len(module.support) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit keine Mentoriate für das Modul {module.number}-{module.title} finden.")

        return discord.Embed(title=f"Mentoriate {module.title}",
                             description="\n".join([f"- [{support.title}]({support.url})" for support in module.support]),
                             color=19607, url=module.url)

    @staticmethod
    async def exams(module):
        if len(module.exams) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit keine Prüfungsinformationen für das Modul {module.number}-{module.title} finden.")

        embed = discord.Embed(title=f"Prüfungsinformationen {module.title}",
                             color=19607, url=module.url)

        for exam in module.exams:
            desc = f"- {exam.type}\n"
            if exam.weight and len(exam.weight) > 0 and exam.weight != '-':
                desc += f"- Gewichtung: **{exam.weight}**\n"

            if exam.requirements and len(exam.requirements) > 0 and exam.requirements != 'keine':
                desc += f"- Inhaltliche Voraussetzungen: \n  - {exam.requirements}\n"

            if exam.hard_requirements and len(exam.hard_requirements) > 0 \
                    and exam.hard_requirements != 'keine':
                desc += f"- Formale Voraussetzungen: \n  - {exam.hard_requirements}\n"
            embed.add_field(name=exam.name, value=desc, inline=False)

        return embed

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
    @app_commands.describe(topic="Möchtest du eine bestimmte Rubrik abrufen?",
                           module_nr="Nummer des Moduls, das dich interessiert. (In einem Moduilkanal optional).",
                           public="Sichtbarkeit der Ausgabe: für alle Mitglieder oder nur für dich.")
    async def cmd_module(self, interaction: Interaction, topic: Topics = None, module_nr: int = None,
                         public: bool = True):
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
