import discord
from discord import ButtonStyle, Interaction
from discord.ui import Button, View

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

EDITDROPDOWN = "timer:editselectview:edit_dropdown"
MANUALDROPDOWN = "timer:manualselectview:manual_dropdowm"

TIME = "timer:edit:time"
SESSIONS = "timer:edit:sessions"


class TimerButton(Button):
    def __init__(self, emoji, custom_id, row, disabled, callback):
        super().__init__(emoji=emoji, custom_id=custom_id, row=row, disabled=disabled)
        self.callback = callback

    async def callback(self, interaction):
        await self.callback(interaction)


class TimerView(View):
    def __init__(self, timer):
        super().__init__(timeout=None)
        self.timer = timer

    @discord.ui.button(label="Anmelden", emoji="👍", style=ButtonStyle.green, custom_id=SUBSCRIBE)
    async def btn_subscribe(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        msg_id = str(interaction.message.id)
        if timer := self.timer.running_timers.get(msg_id):
            if str(interaction.user.id) not in timer['registered']:
                timer['registered'].append(str(interaction.user.id))
                self.timer.save()
                name, status, wt, bt, remaining, registered, _ = self.timer.get_details(msg_id)
                embed = self.timer.create_embed(name, status, wt, bt, remaining, registered)
                await interaction.message.edit(embed=embed, view=self.timer.get_view())
                await interaction.followup.send(content="Du hast dich erfolgreich angemeldet", ephemeral=True)
            else:
                await interaction.followup.send(content="Du bist bereits angemeldet.", ephemeral=True)
        else:
            await interaction.followup.send(content="Etwas ist schiefgelaufen...", ephemeral=True)

    @discord.ui.button(label="Abmelden", emoji="👎", style=ButtonStyle.red, custom_id=UNSUBSCRIBE)
    async def btn_unsubscribe(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        msg_id = str(interaction.message.id)
        if timer := self.timer.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.user.id) in registered:
                if len(registered) == 1:
                    await self.timer.on_stop(button, interaction)
                    return
                else:
                    timer['registered'].remove(str(interaction.user.id))
                    self.timer.save()
                    name, status, wt, bt, remaining, registered, _ = self.timer.get_details(msg_id)
                    embed = self.timer.create_embed(name, status, wt, bt, remaining, registered)
                    await interaction.message.edit(embed=embed, view=self.timer.get_view())
                    await interaction.followup.send(content="Du hast dich erfolgreich abgemeldet", ephemeral=True)
            else:
                await interaction.followup.send(content="Du warst gar nicht angemeldet.", ephemeral=True)
        else:
            await interaction.followup.send(content="Etwas ist schiefgelaufen...", ephemeral=True)

    @discord.ui.button(label="Phase überspringen", emoji="⏩", style=ButtonStyle.blurple, custom_id=SKIP)
    async def btn_skip(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        msg_id = str(interaction.message.id)
        if timer := self.timer.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.user.id) in timer['registered']:
                new_phase = await self.timer.switch_phase(msg_id)
                if new_phase == "Pause":
                    await self.timer.make_sound(registered, 'groove-intro.mp3')
                else:
                    await self.timer.make_sound(registered, 'roll_with_it-outro.mp3')
            else:
                await interaction.followup.send(content="Nur angemeldete Personen können den Timer bedienen.",
                                                ephemeral=True)
        else:
            await interaction.followup.send("Etwas ist schiefgelaufen...", ephemeral=True)

    @discord.ui.button(label="Neustarten", emoji="🔄", style=ButtonStyle.blurple, custom_id=RESTART)
    async def btn_restart(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        msg_id = str(interaction.message.id)
        if timer := self.timer.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.user.id) in timer['registered']:
                timer['status'] = 'Arbeiten'
                timer['remaining'] = timer['working_time']
                self.timer.save()

                await self.timer.edit_message(msg_id)
                await self.timer.make_sound(registered, 'roll_with_it-outro.mp3')
            else:
                await interaction.followup.send(content="Nur angemeldete Personen können den Timer neu starten.",
                                                ephemeral=True)
        else:
            await interaction.followup.send(content="Etwas ist schiefgelaufen...", ephemeral=True)

    @discord.ui.button(label="Beenden", emoji="🛑", style=ButtonStyle.grey, custom_id=STOP)
    async def btn_stop(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        msg_id = str(interaction.message.id)
        if timer := self.timer.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.user.id) in timer['registered']:
                mentions = self.timer.get_mentions(msg_id)
                timer['status'] = "Beendet"
                timer['remaining'] = 0
                timer['registered'] = []

                if new_msg_id := await self.timer.edit_message(msg_id, mentions=mentions):
                    await self.timer.make_sound(registered, 'applause.mp3')
                    self.timer.running_timers.pop(new_msg_id)
                    self.timer.save()
            else:
                # Reply with a hidden message
                await interaction.followup.send(content="Nur angemeldete Personen können den Timer beenden.",
                                                ephemeral=True)
        else:
            await interaction.followup.send(content="Etwas ist schiefgelaufen...", ephemeral=True)

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
    def __init__(self, callback, infos):

        time_input = TextInput(label="Gelernte Zeit in Minuten:",
                               value=f"{infos['time']}",
                               custom_id=TIME,
                               style=TextInputStyle.short,
                               max_length=3)

        session_input = TextInput(label="Anzahl der Sessions:",
                                   value=f"{infos['sessions']}",
                                   custom_id=SESSIONS,
                                   style=TextInputStyle.short,
                                   max_length=1)

        components = [time_input, session_input]

        super().__init__(title=f"Statistik vom {infos['date']} für {infos['name']}",
                         custom_id=f"{infos['id']}:{infos['date']}:{infos['name']}",
                         components=components)
        self.callback = callback
        self.infos = infos

    async def callback(self, interaction: disnake.ModalInteraction):
        await self.callback(interaction=interaction)
