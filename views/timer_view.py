import discord
from discord import ButtonStyle, Interaction
from discord.ui import Button, View

SUBSCRIBE = "timerview:subscribe"
UNSUBSCRIBE = "timerview:unsubscribe"
SKIP = "timverview:skip"
RESTART = "timverview:restart"
STOP = "timverview:stop"


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
