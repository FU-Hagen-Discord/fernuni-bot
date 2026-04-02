import asyncio
import logging
import re
from urllib.parse import quote

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

import utils
from models import Module, Course, ModuleCourse
from module_scraper import Scraper
from transformers import ModuleInformationNotFoundError, ModuleTransformer

_log = logging.getLogger(__name__)


class NoCourseChannelError(Exception):
    pass



class ModuleInformation(commands.GroupCog, name="module", description="Modulinformationen von der Fakultätswebseite."):
    def __init__(self, bot):
        self.bot = bot
        self.scraper = Scraper()
        self.update_lock = asyncio.Lock()
        self.update_loop.start()

    @tasks.loop(hours=24)
    async def update_loop(self):
        await self.update_module_data()

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()

    async def update_module_data(self) -> bool:
        async with self.update_lock:
            try:
                await self.scraper.scrape()
                return True
            except Exception:
                _log.exception("Module data update failed")
                return False

    @staticmethod
    async def find_module(channel, number):
        if not number:
            try:
                number = re.search(r"^([0-9]*)-", channel.name)[1]
            except TypeError:
                raise NoCourseChannelError

        # At this point we can be sure to have a number. Either passed in from the user as argument or from the channel name
        return ModuleTransformer.resolve_module(int(number))

    @staticmethod
    async def exams(module):
        if len(module.exams) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich kann leider derzeit keine Prüfungsinformationen für das Modul {module.number}-{module.title} finden.")

        study_programs = [
            exam.study_program or exam.name
            for exam in module.exams
            if (exam.study_program or exam.name) and len((exam.study_program or exam.name).strip()) > 0
        ]
        unique_study_programs = list(dict.fromkeys(study_programs))
        if len(unique_study_programs) == 0:
            raise ModuleInformationNotFoundError(
                f"Ich konnte leider keine Studiengänge für die Prüfung im Modul {module.number}-{module.title} finden.")

        embed = discord.Embed(title=f"Prüfungsinformationen {module.title}",
                              color=19607, url=module.url)

        embed.add_field(
            name="Studiengänge",
            value="\n".join([f"- {study_program}" for study_program in unique_study_programs]),
            inline=False
        )

        return embed

    @staticmethod
    def build_study_program_url(module_url: str, course_short: str) -> str:
        base_url = module_url.split("?", 1)[0]
        return f"{base_url}?sg={quote(course_short)}"

    @staticmethod
    def get_study_programs_for_module(module: Module) -> list[str]:
        courses = (
            Course.select(Course.short, Course.name)
            .join(ModuleCourse)
            .where(ModuleCourse.module == module)
            .order_by(Course.name)
        )

        return [
            f"[{course.name}]({ModuleInformation.build_study_program_url(module.url, course.short)})"
            for course in courses
        ]

    async def get_embed(self, module: Module):
        embed = discord.Embed(title=f"Modul {module.title}",
                              color=19607)
        embed.add_field(name="Modulnummer", value=str(module.number), inline=False)

        study_programs = self.get_study_programs_for_module(module)
        embed.add_field(
            name="Studiengänge",
            value="\n".join(
                [f"- {program}" for program in study_programs]) if study_programs else "Keine Zuordnung hinterlegt.",
            inline=False,
        )

        return embed

    @app_commands.command(name="info",
                          description="Erhalte die Modulinformationen von der Uniwebseite.")
    @app_commands.describe(
        module_nr="Moduls für das die Informationen angezeigt werden sollen. (In einem Moduilkanal optional).",
                           public="Sichtbarkeit der Ausgabe: für alle Mitglieder oder nur für dich.")
    async def cmd_module_info(self, interaction: Interaction,
                              module_nr: app_commands.Transform[Module, ModuleTransformer] = None,
                              public: bool = True):
        await interaction.response.defer(ephemeral=not public)

        try:
            module = module_nr or await self.find_module(interaction.channel, None)
            embed = await self.get_embed(module)
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

    @cmd_module_info.error
    async def cmd_module_info_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, ModuleInformationNotFoundError):
            message = error.args[0] if error.args and error.args[0] else "Ich konnte das gewünschte Modul nicht finden."
            if interaction.response.is_done():
                await interaction.edit_original_response(content=message)
            else:
                await interaction.response.send_message(content=message, ephemeral=True)
            return

        raise error

    @app_commands.command(name="update", description="Aktualisiert die Moduldaten von der Fakultätswebseite.")
    @utils.mod_only()
    async def cmd_update_modules(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if await self.update_module_data():
            await interaction.edit_original_response(content="Die Moduldaten wurden erfolgreich aktualisiert.")
        else:
            await interaction.edit_original_response(content="Die Aktualisierung der Moduldaten ist fehlgeschlagen.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModuleInformation(bot))
