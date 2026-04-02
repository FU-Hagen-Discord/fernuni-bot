import discord
from discord import Interaction, app_commands

from models import Module


class ModuleInformationNotFoundError(Exception):
    pass


class ModuleTransformer(app_commands.Transformer):
    @property
    def type(self):
        return discord.AppCommandOptionType.integer

    @staticmethod
    def _module_choice_label(module: Module) -> str:
        label = f"{module.number} - {module.title}"
        return label if len(label) <= 100 else f"{label[:97]}..."

    @staticmethod
    def resolve_module(number: int) -> Module:
        number = int(number)

        if module := Module.get_or_none(Module.number == number):
            return module

        raise ModuleInformationNotFoundError(
            f"Ich konnte kein Modul mit der Nummer `{number}` finden. "
            f"Bitte prüfe die Nummer oder wähle ein Modul direkt aus der Vorschlagsliste."
        )

    async def transform(self, interaction: Interaction, value: int, /) -> Module:
        del interaction
        return self.resolve_module(value)

    async def autocomplete(self, interaction: Interaction, value: int | float | str, /) -> list[
        app_commands.Choice[int]]:
        del interaction

        query = str(value or "").strip().lower()
        modules = list(Module.select().order_by(Module.number))

        if query:
            number_prefix_matches = [
                module for module in modules
                if str(module.number).startswith(query)
            ]
            title_matches = [
                module for module in modules
                if query in module.title.lower() and module not in number_prefix_matches
            ]
            modules = number_prefix_matches + title_matches

        return [
            app_commands.Choice[int](name=self._module_choice_label(module), value=module.number)
            for module in modules[:25]
        ]
