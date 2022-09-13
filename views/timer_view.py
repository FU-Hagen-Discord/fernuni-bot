import discord
from discord import MessageInteraction, ButtonStyle
from discord.ui import Button, View

SUBSCRIBE = "timerview:subscribe"
UNSUBSCRIBE = "timerview:unsubscribe"
SKIP = "timverview:skip"
RESTART = "timverview:restart"
STOP = "timverview:stop"


class TimerView(View):
    def __init__(self, callback):
        super().__init__(timeout=None)
        self.callback = callback

    @discord.ui.button(emoji="👍", style=ButtonStyle.grey, custom_id=SUBSCRIBE)
    async def btn_subscribe(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @discord.ui.button(emoji="👎", style=ButtonStyle.grey, custom_id=UNSUBSCRIBE)
    async def btn_unsubscribe(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @discord.ui.button(emoji="⏩", style=ButtonStyle.grey, custom_id=SKIP)
    async def btn_skip(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @discord.ui.button(emoji="🔄", style=ButtonStyle.grey, custom_id=RESTART)
    async def btn_restart(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @discord.ui.button(emoji="🛑", style=ButtonStyle.grey, custom_id=STOP)
    async def btn_stop(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    def disable(self):
        for button in self.children:
            button.disabled = True
