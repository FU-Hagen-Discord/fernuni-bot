import discord
from discord import ButtonStyle


class DialogView(discord.ui.View):

    def __init__(self, buttons=None, callback=None):
        super().__init__(timeout=None)
        self.callback = callback
        for button_config in buttons:
            self.add_button(button_config)

    def add_button(self, config):
        button = discord.ui.Button(
            style=config.get("style", ButtonStyle.grey),
            label=config.get("label", None),
            disabled=config.get("disabled", False),
            custom_id=config.get("custom_id", None),
            url=config.get("url", None),
            emoji=config.get("emoji", None),
            row=config.get("row", None)
        )
        button.value = config.get("value")
        if self.callback:
            button.callback = self.internal_callback(button)
        self.add_item(button)

    def internal_callback(self, button):
        async def button_callback(interaction):
            await self.callback(button, interaction, value=button.value)

        return button_callback
