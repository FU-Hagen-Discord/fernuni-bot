import disnake
from disnake import MessageInteraction, ButtonStyle
from disnake.ui import Button


class TimerView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @disnake.ui.button(emoji="👍", style=ButtonStyle.grey, custom_id="timerview:subscribe")
    async def btn_subscribe(self, button: Button, interaction: MessageInteraction):
        print(interaction.id, interaction.token)
        self.bot.dispatch("timerview_subscribe", button, interaction)
        # await interaction.response.defer(ephemeral=True)

    @disnake.ui.button(emoji="👎", style=ButtonStyle.grey, custom_id="timerview:unsubscribe")
    async def btn_unsubscribe(self, button: Button, interaction: MessageInteraction):
        self.bot.dispatch("timerview_unsubscribe", button, interaction)

    @disnake.ui.button(emoji="⏩", style=ButtonStyle.grey, custom_id="timverview:skip")
    async def btn_skip(self, button: Button, interaction: MessageInteraction):
        self.bot.dispatch("timerview_skip", button, interaction)

    @disnake.ui.button(emoji="🔄", style=ButtonStyle.grey, custom_id="timerview:restart")
    async def btn_restart(self, button: Button, interaction: MessageInteraction):
        self.bot.dispatch("timerview_restart", button, interaction)

    @disnake.ui.button(emoji="🛑", style=ButtonStyle.grey, custom_id="timerview:stop")
    async def btn_stop(self, button: Button, interaction: MessageInteraction):
        self.bot.dispatch("timerview_stop", button, interaction)
