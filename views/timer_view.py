import disnake
from disnake import MessageInteraction, ButtonStyle
from disnake.ui import Button


class TimerView(disnake.ui.View):

    @disnake.ui.button(emoji="👍", style=ButtonStyle.grey, custom_id="timerview:subscribe")
    async def btn_subscribe(self, button: Button, interaction: MessageInteraction):
        pass

    @disnake.ui.button(emoji="👎", style=ButtonStyle.grey, custom_id="timerview:unsubscribe")
    async def btn_unsubscribe(self, button: Button, interaction: MessageInteraction):
        pass

    @disnake.ui.button(emoji="⏩", style=ButtonStyle.grey, custom_id="timverview:skip")
    async def btn_skip(self, button: Button, interaction: MessageInteraction):
        pass

    @disnake.ui.button(emoji="🔄", style=ButtonStyle.grey, custom_id="timerview:restart")
    async def btn_restart(self, button: Button, interaction: MessageInteraction):
        pass

    @disnake.ui.button(emoji="🛑", style=ButtonStyle.grey, custom_id="timerview:stop")
    async def btn_stop(self, button: Button, interaction: MessageInteraction):
        pass
