import disnake
from disnake import MessageInteraction, ButtonStyle
from disnake.ui import Button


class ConfirmView(disnake.ui.View):
    def __init__(self, callback=None):
        super().__init__(timeout=None)
        self.callback = callback

    @disnake.ui.button(emoji="👍", style=ButtonStyle.grey)
    async def btn_subscribe(self, button: Button, interaction: MessageInteraction):
        if self.callback:
            await self.callback(True, button, interaction)

    @disnake.ui.button(emoji="👎", style=ButtonStyle.grey)
    async def btn_unsubscribe(self, button: Button, interaction: MessageInteraction):
        if self.callback:
            await self.callback(False, button, interaction)