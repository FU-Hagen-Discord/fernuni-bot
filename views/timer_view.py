import disnake
from disnake import MessageInteraction, SelectOption
from disnake.ui import Button, View, Modal

VOICY = "timerview:voicy"
SOUND = "timerview:sound"
STATS = "timerview:stats"
MANUAL = "timerview:manual"

SUBSCRIBE = "timerview:subscribe"
RESTART = "timerview:restart"
SKIP = "timverview:skip"
STOP = "timverview:stop"

RESTART_YES = "timerview:restart_yes"
RESTART_NO = "timerview:restart_no"

EDITDROPDOWN = "editselectview:edit_dropdown"
MANUALDROPDOWN = "manualselectview:manual_dropdowm"


class TimerButton(Button):
    def __init__(self, emoji, custom_id, row, disabled, callback):
        super().__init__(emoji=emoji, custom_id=custom_id, row=row, disabled=disabled)
        self.callback = callback

    async def callback(self, interaction):
        await self.callback(interaction)


class TimerView(View):
    def __init__(self, callback, voicy):
        super().__init__(timeout=None)
        self.callback = callback
        self.voicy_emoji = "🔇" if voicy else "🔊"
        self.disable_soundschemes = not voicy

        custom_ids = [VOICY, SOUND, STATS, MANUAL, SUBSCRIBE, RESTART, SKIP, STOP]
        emojis = [self.voicy_emoji, "🎶", "📈", "⁉", "👋", "🔄", "⏩", "🛑"]

        for i in range(8):
            self.add_item(TimerButton(
                emoji=emojis[i],
                custom_id=custom_ids[i],
                row=2 if i<4 else 1,
                disabled= True if ((not voicy) and i==1) else False,
                callback=self.callback
            ))

    def disable(self):
        for button in self.children:
            button.disabled = True


class ManualSelectView(View):
    def __init__(self, callback):
        super().__init__(timeout=None)
        self.callback = callback

    @disnake.ui.select(custom_id=MANUALDROPDOWN,
                       placeholder="wähle hier eine Option aus",
                       min_values=1,
                       max_values=1,
                       options=[SelectOption(label="👋 beim Timer an-/abmelden", value="subscribe"),
                                SelectOption(label="🔄 Session neu starten", value="restart"),
                                SelectOption(label="⏩ Phase überspringen", value="skip"),
                                SelectOption(label="🛑 Timer beenden", value="stop"),
                                SelectOption(label="🔊/🔇 Voicy-Option", value="voicy"),
                                SelectOption(label="🎶 Soundschema", value="sound"),
                                SelectOption(label="📈 Statistik", value="stats")])
    async def sel_manual(self, option: SelectOption, interaction: MessageInteraction):
        await self.callback(option, interaction)


class RestartConfirmView(View):
    def __init__(self, timer_id, callback):
        super().__init__(timeout=None)
        self.callback = callback
        self.timer_id = timer_id

    @disnake.ui.button(emoji="👍", custom_id=RESTART_YES)
    async def btn_restart_yes(self, button: Button, interaction: MessageInteraction):
        await self.callback(interaction, self.timer_id)

    @disnake.ui.button(emoji="👎", custom_id=RESTART_NO)
    async def btn_restart_no(self, button: Button, interaction: MessageInteraction):
        await self.callback(interaction, self.timer_id)

    def disable(self):
        for button in self.children:
            button.disabled = True


class EditSelectView(View):
    def __init__(self, callback, label_list, value_list, further_info=None):
        super().__init__(timeout=None)
        self.callback = callback
        self.label_list = label_list
        self.value_list = value_list
        self.further_info = further_info

        select_menu = self.children[0]
        for i in range(len(label_list)):
            select_menu.add_option(label=self.value_list[i], value=self.label_list[i])

    @disnake.ui.select(custom_id=EDITDROPDOWN,
                       placeholder="Wähle aus",
                       min_values=1,
                       max_values=1)
    async def sel_manual(self, option: SelectOption, interaction: MessageInteraction):
        if self.further_info:
            await self.callback(option, interaction, self.further_info)
        else:
            await self.callback(option, interaction)


class StatsEditModal(Modal):
    def __init__(self, callback, components):
        super().__init__(title="",
                         custom_id="",
                         components=components)
        self.callback = callback
