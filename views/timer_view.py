from datetime import datetime, timedelta

import disnake
from disnake import errors, Embed, Colour


class TimerView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(emoji="👍", style=disnake.ButtonStyle.grey, custom_id="timerview:subscribe")
    async def btn_subscribe(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Angemeldet", ephemeral=True)

    @disnake.ui.button(emoji="👎", style=disnake.ButtonStyle.grey, custom_id="timerview:unsubscribe")
    async def btn_unsubscribe(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Abgemeldet", ephemeral=True)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.grey, custom_id="timverview:skip")
    async def btn_skip(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Geskipped", ephemeral=True)

    @disnake.ui.button(emoji="🔄", style=disnake.ButtonStyle.grey, custom_id="timerview:restart")
    async def btn_restart(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Neugestartet", ephemeral=True)

    @disnake.ui.button(emoji="🛑", style=disnake.ButtonStyle.grey, custom_id="timerview:stop")
    async def btn_stop(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Beendet", ephemeral=True)

    async def send_message(self, channel: disnake.abc.Messageable, name: str, status: str, working_time: int,
                           break_time: int, remaining: int, registered: [str]):
        embed = self.create_embed(name, status, working_time, break_time, remaining, registered)
        return await channel.send(embed=embed, view=self)

    def create_embed(self, name, status, working_time, break_time, remaining, registered):
        color = Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else Colour.red()
        descr = f"👍 beim Timer anmelden\n\n" \
                f"👎 beim Timer abmelden\n\n" \
                f"⏩ Phase überspringen\n\n" \
                f"🔄 Timer neu starten\n\n" \
                f"🛑 Timer beenden\n"
        zeiten = f"{working_time} Minuten Arbeiten\n{break_time} Minuten Pause"
        remaining_value = f"{remaining} Minuten"
        endzeit = (datetime.now() + timedelta(minutes=remaining)).strftime("%H:%M")
        end_value = f" [bis {endzeit} Uhr]" if status != "Beendet" else ""
        user_list = [self.bot.get_user(int(user_id)) for user_id in registered]
        angemeldet_value = ", ".join([user.mention for user in user_list])

        embed = Embed(title=name,
                      description=f'Jetzt: {status}',
                      color=color)
        embed.add_field(name="Bedienung:", value=descr, inline=False)
        embed.add_field(name="Zeiten:", value=zeiten, inline=False)
        embed.add_field(name="verbleibende Zeit:", value=remaining_value + end_value, inline=False)
        embed.add_field(name="angemeldete User:", value=angemeldet_value if registered else "-", inline=False)

        return embed
