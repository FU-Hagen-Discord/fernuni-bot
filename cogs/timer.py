import json
import os
import random
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta

import disnake
from disnake import MessageInteraction, ApplicationCommandInteraction
from disnake.ext import commands, tasks
from disnake.ui import Button

from views import timer_view


class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.default_names = ["Rapunzel", "Aschenputtel", "Schneewittchen", "Frau Holle", "Schneeweißchen und Rosenrot",
                              "Gestiefelter Kater", "Bremer Stadtmusikanten"]
        self.timer_file_path = os.getenv("DISCORD_TIMER_FILE")
        self.running_timers = self.load()
        self.load()
        self.run_timer.start()

    def load(self):
        with open(self.timer_file_path, mode='r') as timer_file:
            return json.load(timer_file)

    def save(self):
        with open(self.timer_file_path, mode='w') as timer_file:
            json.dump(self.running_timers, timer_file)

    def get_view(self, disabled=False):
        view = timer_view.TimerView(callback=self.on_button_click)

        if disabled:
            view.disable()

        return view

    async def on_button_click(self, button: Button, interaction: MessageInteraction):
        custom_id = button.custom_id

        if custom_id == timer_view.SUBSCRIBE:
            await self.on_subscribe(button, interaction)
        elif custom_id == timer_view.UNSUBSCRIBE:
            await self.on_unsubscribe(button, interaction)
        elif custom_id == timer_view.SKIP:
            await self.on_skip(button, interaction)
        elif custom_id == timer_view.RESTART:
            await self.on_restart(button, interaction)
        elif custom_id == timer_view.STOP:
            await self.on_stop(button, interaction)

    async def on_subscribe(self, button: Button, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(interaction.author.id) not in timer['registered']:
                timer['registered'].append(str(interaction.author.id))
                self.save()
                name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered)
                await interaction.message.edit(embed=embed, view=self.get_view())
                await interaction.response.send_message("Du hast dich erfolgreich angemeldet", ephemeral=True)
            else:
                await interaction.response.send_message("Du bist bereits angemeldet.", ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_unsubscribe(self, button: Button, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in registered:
                if len(registered) == 1:
                    await self.on_stop(button, interaction)
                    return
                else:
                    timer['registered'].remove(str(interaction.author.id))
                    self.save()
                    name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                    embed = self.create_embed(name, status, wt, bt, remaining, registered)
                    await interaction.message.edit(embed=embed, view=self.get_view())
                    await interaction.response.send_message("Du hast dich erfolgreich abgemeldet", ephemeral=True)
            else:
                await interaction.response.send_message("Du warst gar nicht angemeldet.", ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_skip(self, button: Button, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in timer['registered']:
                new_phase = await self.switch_phase(msg_id)
                if new_phase == "Pause":
                    await self.make_sound(registered, 'groove-intro.mp3')
                else:
                    await self.make_sound(registered, 'roll_with_it-outro.mp3')
                await interaction.response.send_message("Erfolgreich übersprungen", ephemeral=True)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer bedienen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_restart(self, button: Button, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in timer['registered']:
                timer['status'] = 'Arbeiten'
                timer['remaining'] = timer['working_time']
                self.save()

                await self.edit_message(msg_id)
                await self.make_sound(registered, 'roll_with_it-outro.mp3')
                await interaction.response.send_message("Erfolgreich neugestartet", ephemeral=True)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer neu starten.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_stop(self, button: Button, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in timer['registered']:
                mentions = self.get_mentions(msg_id)
                timer['status'] = "Beendet"
                timer['remaining'] = 0
                timer['registered'] = []

                await interaction.response.send_message("Erfolgreich beendet", ephemeral=True)
                if new_msg_id := await self.edit_message(msg_id, mentions=mentions):
                    await self.make_sound(registered, 'applause.mp3')
                    self.running_timers.pop(new_msg_id)
                    self.save()
            else:
                # Reply with a hidden message
                await interaction.response.send_message("Nur angemeldete Personen können den Timer beenden.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    def create_embed(self, name, status, working_time, break_time, remaining, registered):
        color = disnake.Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else disnake.Colour.red()
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

        embed = disnake.Embed(title=name,
                              description=f'Jetzt: {status}',
                              color=color)
        embed.add_field(name="Bedienung:", value=descr, inline=False)
        embed.add_field(name="Zeiten:", value=zeiten, inline=False)
        embed.add_field(name="verbleibende Zeit:", value=remaining_value + end_value, inline=False)
        embed.add_field(name="angemeldete User:", value=angemeldet_value if registered else "-", inline=False)

        return embed

    @commands.slash_command(name="timer", description="Erstelle deine persönliche  Eieruhr")
    async def cmd_timer(self, interaction: ApplicationCommandInteraction, working_time: int = 25,
                        break_time: int = 5,
                        name: str = None):
        name = name if name else random.choice(self.default_names)
        remaining = working_time
        status = "Arbeiten"
        registered = [str(interaction.author.id)]

        embed = self.create_embed(name, status, working_time, break_time, remaining, registered)
        await interaction.response.send_message(embed=embed, view=self.get_view())
        message = await interaction.original_message()

        self.running_timers[str(message.id)] = {'name': name,
                                                'status': status,
                                                'working_time': working_time,
                                                'break_time': break_time,
                                                'remaining': remaining,
                                                'registered': registered,
                                                'channel': interaction.channel_id}
        self.save()
        await self.make_sound(registered, 'roll_with_it-outro.mp3')

    async def switch_phase(self, msg_id):
        if timer := self.running_timers.get(msg_id):
            if timer['status'] == "Arbeiten":
                timer['status'] = "Pause"
                timer['remaining'] = timer['break_time']
            elif timer['status'] == "Pause":
                timer['status'] = "Arbeiten"
                timer['remaining'] = timer['working_time']
            else:
                self.running_timers.pop(msg_id)
                return "Beendet"
            self.save()

            if new_msg_id := await self.edit_message(msg_id):
                return self.running_timers[new_msg_id]['status']
            else:
                return "Beendet"

    def get_details(self, msg_id):
        name = self.running_timers[msg_id]['name']
        status = self.running_timers[msg_id]['status']
        wt = self.running_timers[msg_id]['working_time']
        bt = self.running_timers[msg_id]['break_time']
        remaining = self.running_timers[msg_id]['remaining']
        registered = self.running_timers[msg_id]['registered']
        channel = self.running_timers[msg_id]['channel']
        return name, status, wt, bt, remaining, registered, channel

    async def edit_message(self, msg_id, mentions=None, create_new=True):
        if timer := self.running_timers.get(msg_id):
            channel_id = timer['channel']
            channel = await self.bot.fetch_channel(int(channel_id))
            try:
                msg = await channel.fetch_message(int(msg_id))

                name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered)

                if create_new:
                    await msg.delete()
                    if not mentions:
                        mentions = self.get_mentions(msg_id)
                    if status == "Beendet":
                        new_msg = await channel.send(mentions, embed=embed,
                                                     view=self.get_view(disabled=True))
                    else:
                        new_msg = await channel.send(mentions, embed=embed, view=self.get_view())
                    self.running_timers[str(new_msg.id)] = self.running_timers[msg_id]
                    self.running_timers.pop(msg_id)
                    self.save()
                    msg = new_msg
                else:
                    await msg.edit(embed=embed, view=self.get_view())
                return str(msg.id)
            except disnake.errors.NotFound:
                self.running_timers.pop(msg_id)
                self.save()
                return None

    def get_mentions(self, msg_id):
        guild = self.bot.get_guild(self.guild_id)
        registered = self.running_timers.get(msg_id)['registered']
        members = [guild.get_member(int(user_id)) for user_id in registered]
        mentions = ", ".join([member.mention for member in members])
        return mentions

    async def make_sound(self, registered_users, filename):
        guild = self.bot.get_guild(self.guild_id)
        for user_id in registered_users:
            member = guild.get_member(int(user_id))
            if member.voice:
                channel = member.voice.channel
                if channel:  # If user is in a channel
                    try:
                        voice_client = await channel.connect()
                        voice_client.play(disnake.FFmpegPCMAudio(f'cogs/sounds/{filename}'))
                        await sleep(3)
                    except disnake.errors.ClientException as e:
                        print(e)
                    for vc in self.bot.voice_clients:
                        await vc.disconnect()
                break

    @tasks.loop(minutes=1)
    async def run_timer(self):
        timers_copy = deepcopy(self.running_timers)
        for msg_id in timers_copy:
            registered = self.running_timers[msg_id]['registered']
            self.running_timers[msg_id]['remaining'] -= 1
            if self.running_timers[msg_id]['remaining'] <= 0:
                new_phase = await self.switch_phase(msg_id)
                if new_phase == "Pause":
                    await self.make_sound(registered, 'groove-intro.mp3')
                elif new_phase == "Arbeiten":
                    await self.make_sound(registered, 'roll_with_it-outro.mp3')
            else:
                await self.edit_message(msg_id, create_new=False)

    @run_timer.before_loop
    async def before_timer(self):
        await sleep(60)

    @cmd_timer.error
    async def timer_error(self, ctx, error):
        await ctx.send("Das habe ich nicht verstanden. Die Timer-Syntax ist:\n"
                       "`!timer <learning-time?> <break-time?> <name?>`\n")