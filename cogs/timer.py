import json
import os
import random
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta

import disnake
from disnake import MessageInteraction, ApplicationCommandInteraction
from disnake.ext import commands, tasks
from disnake.ui import Button, Select

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

    def get_view(self, disabled=False, voicy=False):

        view = timer_view.TimerView(callback=self.on_button_click, voicy=voicy)

        if disabled:
            view.disable()

        return view

    async def on_button_click(self, interaction: MessageInteraction):
        custom_id = interaction.data.custom_id

        if custom_id == timer_view.SUBSCRIBE:
            await self.on_subscribe(interaction)
        elif custom_id == timer_view.UNSUBSCRIBE:
            await self.on_unsubscribe(interaction)
        elif custom_id == timer_view.SKIP:
            await self.on_skip(interaction)
        elif custom_id == timer_view.STOP:
            await self.on_stop(interaction)
        elif custom_id == timer_view.VOICY:
            await self.on_voicy(interaction)
        elif custom_id == timer_view.SOUND:
            await self.on_sound(interaction)
        elif custom_id == timer_view.STATS:
            await self.on_stats(interaction)
        elif custom_id == timer_view.MANUAL:
            await self.on_manual(interaction)

    async def on_subscribe(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(interaction.author.id) not in timer['registered']:
                timer['registered'].append(str(interaction.author.id))
                self.save()
                name, status, wt, bt, remaining, registered, _, voicy, sound = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered, voicy, sound)
                await interaction.message.edit(embed=embed, view=self.get_view(voicy=voicy))
                await interaction.response.send_message("Du hast dich erfolgreich angemeldet", ephemeral=True)
            else:
                await interaction.response.send_message("Du bist bereits angemeldet.", ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_unsubscribe(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in registered:
                if len(registered) == 1:
                    await self.on_stop(interaction)
                    return
                else:
                    timer['registered'].remove(str(interaction.author.id))
                    self.save()
                    name, status, wt, bt, remaining, registered, _, voicy, sound = self.get_details(msg_id)
                    embed = self.create_embed(name, status, wt, bt, remaining, registered, voicy, sound)
                    await interaction.message.edit(embed=embed, view=self.get_view(voicy=voicy))
                    await interaction.response.send_message("Du hast dich erfolgreich abgemeldet", ephemeral=True)
            else:
                await interaction.response.send_message("Du warst gar nicht angemeldet.", ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_skip(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in timer['registered']:
                new_phase = await self.switch_phase(msg_id)
                if timer['voicy']:
                    await interaction.response.send_message("Erfolgreich übersprungen", ephemeral=True)
                    if new_phase == "Pause":
                        await self.make_sound(registered, f"{timer['sound']}/pause.mp3")
                    else:
                        await self.make_sound(registered, f"{timer['sound']}/learning.mp3")
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer bedienen.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_stop(self, interaction: MessageInteraction):
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
                    if timer['voicy']:
                        await self.make_sound(registered, 'applause.mp3')
                    self.running_timers.pop(new_msg_id)
                    self.save()
            else:
                # Reply with a hidden message
                await interaction.response.send_message("Nur angemeldete Personen können den Timer beenden.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_voicy(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(interaction.author.id) in timer['registered']:
                voicy = timer['voicy']
                timer['voicy'] = not voicy
                self.save()
                await self.edit_message(msg_id, create_new=False)
                await interaction.response.send_message("Voicy-Option erfolgreich geändert.", ephemeral=True)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer bedienen.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_sound(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(interaction.author.id) in timer['registered']:
                soundschemes = [scheme for scheme in os.listdir("./cogs/sounds") if scheme != 'applause.mp3']
                current = soundschemes.index(timer['sound'])
                next = (current + 1) % len(soundschemes)
                timer['sound'] = soundschemes[next]
                self.save()
                await self.edit_message(msg_id, create_new=False)
                await interaction.response.send_message("Soundschema erfolgreich geändert.", ephemeral=True)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer bedienen.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_stats(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(interaction.author.id) in timer['registered']:
                pass
                # TODO
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer bedienen.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_manual(self, interaction: MessageInteraction):
        manual_message = f"So kannst du den Timer bedienen:\n\n" \
                         f"👍 beim Timer anmelden\n" \
                         f"👎 beim Timer abmelden\n" \
                         f"⏩ Phase überspringen\n" \
                         f"🛑 Timer beenden\n" \
                         f"🔊 Sound abspielen bei Phasenwechsel\n" \
                         f"🔇 Keinen Sound abspielen\n" \
                         f"🎶 Soundschema auswählen\n" \
                         f"📈 Timersession in die Statistik aufnehmen\n\n" \
                         f"Für detailliertere Informationen:"

        menu_view = timer_view.ManualSelectView(callback=self.on_manual_select)
        await interaction.response.send_message(manual_message, view=menu_view, ephemeral=True)

    async def on_manual_select(self, select: Select, interaction: MessageInteraction):
        if select.values[0] == "subscribe":
            content = "👍 beim Timer anmelden\n\n" \
                      "Hiermit meldest du dich bei diesem Timer an. \n" \
                      "Du erscheinst dan in der Liste der angemeldeten\n" \
                      "User, wirst angepingt beim Phasenwechsel und \n" \
                      "kannst die anderen Buttons bedienen.\n\n"

        elif select.values[0] == "unsubscribe":
            content = "👎 beim Timer abmelden\n\n" \
                      "Hiermit meldest du dich beim Timer ab.\n" \
                      "Du erscheinst dann nicht mehr in der Liste \n" \
                      "der angemeldeten User, wirst beim Phasenwechsel\n" \
                      "nicht mehr angepingt und kannst die Buttons\n" \
                      "nicht mehr bedienen.\n\n"

        elif select.values[0] == "skip":
            content = "⏩ Phase überspringen\n\n" \
                      "Brauchst du eine Pause, obwohl gerade Lernphase \n" \
                      "ist? Oder Willst du weiter lernen, obwohl gerade \n" \
                      "die Pause angefangen hat? Dann ist dieser Button\n" \
                      "der richtige für dich. (Wenn mehrere am Timer \n" \
                      "angemeldet sind, besprich das erst mit den anderen.)\n\n"

        elif select.values[0] == "stop":
            content = f"🛑 Timer beenden\n\n" \
                      f"Fertig für heute? Dieser Button beendet die \n" \
                      f"Timer-Session. Wenn mehrere User am Timer \n" \
                      "angemeldet sind, besprich das erst mit den anderen.\n\n"

        elif select.values[0] == "voicy":
            content = "🔊/🔇 Voicy-Option\n\n" \
                      f"Wenn diese Option eingeschaltet ist, Kommt {self.bot.user.display_name}\n" \
                      f"beim Phasenwechsel in den Voice-Channel in dem\n" \
                      f"ihr euch gerade befindet und spielt einen Sound ab.\n" \
                      f"Ist die Option ausgeschaltet, werdet ihr lediglich \n" \
                      f"angepingt zum Phasenwechsel."

        elif select.values[0] == "sound":
            content = "🎶 Soundschema\n\n" \
                      "Zur Besseren Unterscheidung wenn mehrere Timer mit\n" \
                      "eingeschalteter Voicy-option laufen, kannst du hier\n" \
                      "ein anderes Soundschema auswählen."

        elif select.values[0] == "stats":
            content = "📈 Statistik\n\n" \
                      "Über die Timer-Nutzung wird eine Statistik geführt,\n" \
                      "die kannst du mit dem Kommando `\\timer stats` einsehen.\n" \
                      "Wenn diese Session nicht in die Statistik aufgenommen \n" \
                      "werden soll, ist dies der Button deiner Wahl."

        else:
            content = "Etwas ist schief gelaufen..."

        await interaction.response.edit_message(content=content)

    def create_embed(self, name, status, working_time, break_time, remaining, registered, voicy, sound):
        color = disnake.Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else disnake.Colour.red()

        zeiten = f"{working_time} Minuten Arbeiten\n{break_time} Minuten Pause"
        remaining_value = f"{remaining} Minuten"
        endzeit = (datetime.now() + timedelta(minutes=remaining)).strftime("%H:%M")
        end_value = f" [bis {endzeit} Uhr]" if status != "Beendet" else ""
        user_list = [self.bot.get_user(int(user_id)) for user_id in registered]
        angemeldet_value = ", ".join([user.mention for user in user_list])
        voicy_info = "🔊 Soundwiedergabe im Voicy" if voicy else "🔇 Kein Voicy-Beitritt"
        sound_info = f"🎶 {sound}" if voicy else "🎶 -"

        info_value = f"{voicy_info}\n" \
                     f"{sound_info}\n" \
                     f"📈 Session geht in die Statistik ein\n\n" \
                     f"⁉ ruft eine Bedienungsanleitung auf."

        descr = f"Jetzt: {status} {end_value}\n" \
                f"noch {remaining_value}\n\n" \

        embed = disnake.Embed(title=name,
                              description=descr,
                              color=color)

        embed.add_field(name="Zeiten:", value=zeiten, inline=False)
        embed.add_field(name="Infos:", value=info_value, inline=False)
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
        voicy = False
        sound = 'standard'

        embed = self.create_embed(name, status, working_time, break_time, remaining, registered, voicy, sound)
        await interaction.response.send_message(embed=embed, view=self.get_view(voicy=voicy))
        message = await interaction.original_message()

        self.running_timers[str(message.id)] = {'name': name,
                                                'status': status,
                                                'working_time': working_time,
                                                'break_time': break_time,
                                                'remaining': remaining,
                                                'registered': registered,
                                                'channel': interaction.channel_id,
                                                'voicy': voicy,
                                                'sound': sound}
        self.save()

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
        if timer := self.running_timers.get(msg_id):
            name = timer['name']
            status = timer['status']
            wt = timer['working_time']
            bt = timer['break_time']
            remaining = timer['remaining']
            registered = timer['registered']
            channel = timer['channel']
            voicy = timer['voicy']
            sound = timer['sound']
            return name, status, wt, bt, remaining, registered, channel, voicy, sound

    async def edit_message(self, msg_id, mentions=None, create_new=True):
        if timer := self.running_timers.get(msg_id):
            channel_id = timer['channel']
            channel = await self.bot.fetch_channel(int(channel_id))
            try:
                msg = await channel.fetch_message(int(msg_id))

                name, status, wt, bt, remaining, registered, _, voicy, sound = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered, voicy, sound)

                if create_new:
                    await msg.delete()
                    if not mentions:
                        mentions = self.get_mentions(msg_id)
                    if status == "Beendet":
                        new_msg = await channel.send(mentions, embed=embed,
                                                     view=self.get_view(disabled=True, voicy=voicy))
                    else:
                        new_msg = await channel.send(mentions, embed=embed, view=self.get_view(voicy=voicy))
                    self.running_timers[str(new_msg.id)] = self.running_timers[msg_id]
                    self.running_timers.pop(msg_id)
                    self.save()
                    msg = new_msg
                else:
                    await msg.edit(embed=embed, view=self.get_view(voicy=voicy))
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
            timer = self.running_timers[msg_id]
            registered = timer['registered']
            timer['remaining'] -= 1
            if timer['remaining'] <= 0:
                new_phase = await self.switch_phase(msg_id)
                if timer['voicy']:
                    if new_phase == "Pause":
                        await self.make_sound(registered, f"{timer['sound']}/pause.mp3")
                    elif new_phase == "Arbeiten":
                        await self.make_sound(registered, f"{timer['sound']}/learning.mp3")
            else:
                await self.edit_message(msg_id, create_new=False)


    @run_timer.before_loop
    async def before_timer(self):
        await sleep(60)

    @cmd_timer.error
    async def timer_error(self, ctx, error):
        await ctx.send("Das habe ich nicht verstanden. Die Timer-Syntax ist:\n"
                       "`/timer <learning-time?> <break-time?> <name?>`\n")