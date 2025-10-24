import os

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from models import GradeStatisticsImage

class ModuleInformationNotFoundError(Exception):
    pass

class GradeStatistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="klausurstatistiken",
                          description="Erhalte eine Grafik der Klausurstatistiken für ein Modul.")
    @app_commands.describe(modul_nummer="Nummer des Moduls, das dich interessiert.",
                           public="Sichtbarkeit der Ausgabe: für alle Mitglieder oder nur für dich."
                           )
    async def cmd_module(self,
                         interaction: Interaction, 
                         modul_nummer: int = None,
                         public: bool = False):       

        try:
            await interaction.response.defer(ephemeral=not public)
            module = await self.get_statistics_data(modul_nummer)

            with open(module.path, 'rb') as f:
                discord_file = discord.File(f, filename=f"klausurstatistiken.{module.number}.png")
                await interaction.edit_original_response(attachments=[discord_file])
        except:
            await interaction.edit_original_response(content="Leider konnte ich keine Informationen zu diesem Modul/Kurs finden.")

    @staticmethod
    async def get_statistics_data(module_number: int) -> GradeStatisticsImage:
        if module_number is None or module_number <= 0:
            raise ValueError(f"Invalid module number")

        found_module: GradeStatisticsImage = GradeStatisticsImage.get_or_none(GradeStatisticsImage.number == module_number)

        if not found_module:
            raise ModuleInformationNotFoundError(f"Zum Modul mit der Nummer {module_number} konnte ich keine Informationen "
                                                 f"finden. Bitte geh sicher, dass dies ein gültiges Modul ist. "
                                                 f"Ansonsten schreibe mir eine Direktnachricht und ich leite sie "
                                                 f"weiter an das Mod-Team.")

        path_to_plots = os.getenv('PLOTS_PATH')
        path_on_file_system = os.path.join(path_to_plots, str(found_module.path))

        found_module.path = path_on_file_system

        if not os.path.exists(found_module.path):
            raise ModuleInformationNotFoundError(f"Die Grafik für das Modul mit der Nummer {module_number} konnte nicht gefunden werden.")

        return found_module

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GradeStatistics(bot))