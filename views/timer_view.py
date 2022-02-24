import disnake
from disnake import MessageInteraction, SelectOption
from disnake.ui import Button, View

VOICY = "timerview:voicy"
SOUND = "timerview:sound"
STATS = "timerview:stats"
MANUAL = "timerview:manual"

SUBSCRIBE = "timerview:subscribe"
RESTART = "timerview:restart"
SKIP = "timverview:skip"
STOP = "timverview:stop"


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
                disabled= True if ((not voicy) and i==1 or i==2) else False,
                callback=self.callback
            ))

    def disable(self):
        for button in self.children:
            button.disabled = True


class ManualSelectView(View):
    def __init__(self, callback):
        super().__init__(timeout=None)
        self.callback = callback

    @disnake.ui.select(custom_id="manual_dropdown",
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
