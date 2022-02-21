import disnake
from disnake import MessageInteraction, ButtonStyle, SelectOption
from disnake.ui import Button, View, Select

VOICY = "timerview:voicy"
SOUND = "timerview:sound"
STATS = "timerview:stats"
MANUAL = "timerview:manual"

SUBSCRIBE = "timerview:subscribe"
UNSUBSCRIBE = "timerview:unsubscribe"
SKIP = "timverview:skip"
STOP = "timverview:stop"


class TimerView(View):
    def __init__(self, callback):
        super().__init__(timeout=None)
        self.callback = callback

    @disnake.ui.button(emoji="🔊", style=ButtonStyle.grey, custom_id=VOICY, row=1)
    async def btn_voicy(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="🎶", style=ButtonStyle.grey, custom_id=SOUND, row=1, disabled=True)
    async def btn_sound(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="📈", style=ButtonStyle.grey, custom_id=STATS, row=1, disabled=True)
    async def btn_stats(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="⁉", style=ButtonStyle.grey, custom_id=MANUAL, row=1)
    async def btn_manual(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="👍", style=ButtonStyle.grey, custom_id=SUBSCRIBE, row=0)
    async def btn_subscribe(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="👎", style=ButtonStyle.grey, custom_id=UNSUBSCRIBE, row=0)
    async def btn_unsubscribe(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="⏩", style=ButtonStyle.grey, custom_id=SKIP, row=0)
    async def btn_skip(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    @disnake.ui.button(emoji="🛑", style=ButtonStyle.grey, custom_id=STOP, row=0)
    async def btn_stop(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction)

    def disable(self):
        for button in self.children:
            button.disabled = True

    async def change_voicy_button(self, interaction, mute):
        if mute:
            self.children[0].emoji = "🔊"
            self.children[1].disabled = True
        else:
            self.children[0].emoji = "🔇"
            self.children[1].disabled = False
        await interaction.response.edit_message(view=self)

class ManualSelectView(View):
    def __init__(self, callback):
        super().__init__(timeout=None)
        self.callback = callback

    @disnake.ui.select(custom_id="manual_dropdown",
                       placeholder="wähle hier eine Option aus",
                       min_values=1,
                       max_values=1,
                       options=[SelectOption(label="👍 beim Timer anmelden", value="subscribe"),
                                SelectOption(label="👎 beim Timer abmelden", value="unsubscribe"),
                                SelectOption(label="⏩ Phase überspringen", value="skip"),
                                SelectOption(label="🛑 Timer beenden", value="stop"),
                                SelectOption(label="🔊/🔇 Voicy-Option", value="voicy"),
                                SelectOption(label="📈 Statistik", value="stats")])
    async def sel_manual(self, option: SelectOption, interaction: MessageInteraction):
        await self.callback(option, interaction)