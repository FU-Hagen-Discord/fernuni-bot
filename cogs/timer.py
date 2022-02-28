import json
import os
import random
import time
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta

import disnake
from disnake import MessageInteraction, ApplicationCommandInteraction
from disnake.ext import commands, tasks
from disnake.ui import Select

from views import timer_view

"""
  Environment Variablen:
  DISCORD_TIMER_FILE - json file mit allen aktuell laufenden timern
  DISCORD_TIMER_STATS_FILE - json file mit der Timer-Statistik

  Struktur der json:
  {msg_id:{name:<Titel des Timers>, 
           status:<Arbeiten|Pause|Beendet>, 
           working_time:<eingestellte Arbeitszeit in Minuten>, 
           break_time:<eingestellte Pausenzeit in Minuten>,
           end_of_phase:<Zeitstempel der Endzeit der aktuellen Phase>,
           registered:<Liste der angemeldeten User-IDs>,
           channel:<ID des Channels in dem der Timer läuft>,
           voicy:<True|False>,
           sound:<aktuelles Soundschema>,
           into_global_stats: <True|False>,
           session_stats: {'start': <Zeitstempel>, 
                           'learning_phases': <Anzahl der begonnenen Lernphasen>},
           planned_rounds: <Anzahl geplanter Lernphasen für automatisches Beenden
                            oder 0 für manuelles Beenden>}
           
  Neue Soundschemata lassen sich hinzufügen mittels neuem Ordner 'cogs/sounds/<schema>'
  in diesem müssen genau zwei Dateien sein: 'learning.mp3' und 'pause.mp3'
"""


class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.timer_file_path = os.getenv("DISCORD_TIMER_FILE")
        self.stats_file_path = os.getenv("DISCORD_TIMER_STATS_FILE")
        self.default_names = ["Rapunzel", "Aschenputtel", "Schneewittchen", "Frau Holle", "Schneeweißchen und Rosenrot",
                              "Gestiefelter Kater", "Bremer Stadtmusikanten"]
        self.running_timers = {}
        self.stats = {}
        self.load_running_timers()
        self.load_stats()
        self.run_timer.start()

    def load_running_timers(self):
        try:
            with open(self.timer_file_path, mode='r') as timer_file:
                self.running_timers = json.load(timer_file)
        except FileNotFoundError:
            # create file if not found
            self.save_running_timers()

    def load_stats(self):
        try:
            with open(self.stats_file_path, mode='r') as stats_file:
                self.stats = json.load(stats_file)
        except FileNotFoundError:
            # create file if not found
            self.save_stats()

    def save_running_timers(self):
        with open(self.timer_file_path, mode='w') as timer_file:
            json.dump(self.running_timers, timer_file)

    def save_stats(self):
        with open(self.stats_file_path, mode='w') as stats_file:
            json.dump(self.stats, stats_file)

    def get_view(self, disabled=False, voicy=False):
        view = timer_view.TimerView(callback=self.on_button_click, voicy=voicy)
        if disabled:
            view.disable()
        return view

    async def on_button_click(self, interaction: MessageInteraction):
        custom_id = interaction.data.custom_id

        if custom_id == timer_view.SUBSCRIBE:
            await self.on_subscribe(interaction)
        elif custom_id == timer_view.RESTART:
            await self.on_restart(interaction)
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
            registered = timer['registered']
            if str(interaction.author.id) not in registered:
                timer['registered'].append(str(interaction.author.id))
            else:
                if len(registered) == 1:
                    await self.on_stop(interaction)
                    return
                else:
                    timer['registered'].remove(str(interaction.author.id))
            self.save_running_timers()
            name, status, wt, bt, end_of_phase, registered, _, voicy, sound, stats, _ = self.get_details(msg_id)
            embed = self.create_embed(name, status, wt, bt, end_of_phase, registered, voicy, sound, stats)
            await interaction.message.edit(embed=embed, view=self.get_view(voicy=voicy))
            await interaction.response.defer()
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_restart(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(interaction.author.id) in timer['registered']:
                restart_confirm_view = timer_view.RestartConfirmView(timer_id=msg_id, callback=self.on_restart_confirm)
                await interaction.response.send_message("Ein Neustart des Timers setzt auch die aktuelle Session-"
                                                        "Statistik zurück. Möchtest du das?",
                                                        view=restart_confirm_view, ephemeral=True)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer neu starten.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_restart_confirm(self, interaction: MessageInteraction, msg_id):
        restart_confirm_view = timer_view.RestartConfirmView(timer_id=msg_id, callback=self.on_restart_confirm)
        restart_confirm_view.disable()
        if interaction.data.custom_id == timer_view.RESTART_YES:
            timer = self.running_timers.get(msg_id)
            registered = timer['registered']
            timer['status'] = 'Arbeiten'
            timer['end_of_phase'] = datetime.timestamp(datetime.now() + timedelta(timer['working_time']))
            # Statistik zurück setzen
            session_stats = {'start': time.time(), 'rounds': 1}
            timer['session_stats'] = session_stats
            self.save_running_timers()
            await self.edit_message(msg_id)
            if timer['voicy']:
                await self.make_sound(registered, f"{timer['sound']}/learning.mp3")
            await interaction.response.edit_message(content="Timer neu gestartet und Session-Statistik zurück gesetzt,",
                                                    view=restart_confirm_view)
        else:
            await interaction.response.edit_message(content="Timer nicht neu gestartet.", view=restart_confirm_view)

    async def on_skip(self, interaction: MessageInteraction):
        msg_id = str(interaction.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(interaction.author.id) in timer['registered']:
                new_phase = await self.switch_phase(msg_id)
                if timer['voicy']:
                    await interaction.response.defer()
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
                #timer['remaining'] = 0
                timer['registered'] = []

                if new_msg_id := await self.edit_message(msg_id, mentions=mentions):
                    if timer['voicy']:
                        await self.make_sound(registered, 'applause.mp3')
                    self.running_timers.pop(new_msg_id)
                    self.save_running_timers()
                await interaction.response.defer()
                # TODO: Session-Statistik in globale Statistik überführen
                # TODO: Session-Statistik ausgeben
            else:
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
                self.save_running_timers()
                await self.edit_message(msg_id, create_new=False)
                await interaction.response.defer()
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
                self.save_running_timers()
                await self.edit_message(msg_id, create_new=False)
                await interaction.response.defer()
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
                # TODO Toggle Session Statistik
                await interaction.response.send_message("...", ephemeral=True)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer bedienen.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_manual(self, interaction: MessageInteraction):
        manual_message = f"So kannst du den Timer bedienen:\n\n" \
                         f"👋 beim Timer an/abmelden\n" \
                         f"🔄 Session neu starten\n" \
                         f"⏩ Phase überspringen\n" \
                         f"🛑 Timer beenden\n" \
                         f"🔊/🔇 Sound abspielen (oder nicht) bei Phasenwechsel\n" \
                         f"🎶 Soundschema auswählen\n" \
                         f"📈 Session in die Statistik aufnehmen\n\n" \
                         f"Für detailliertere Informationen:"

        menu_view = timer_view.ManualSelectView(callback=self.on_manual_select)
        await interaction.response.send_message(manual_message, view=menu_view, ephemeral=True)

    async def on_manual_select(self, select: Select, interaction: MessageInteraction):
        if select.values[0] == "subscribe":
            content = "👋 beim Timer an-/abmelden\n\n" \
                      "Hiermit meldest du dich bei diesem Timer an (bzw. ab). \n" \
                      "Du erscheinst dann (nicht mehr) in der Liste der angemeldeten\n" \
                      "User, wirst (nicht mehr) angepingt beim Phasenwechsel und \n" \
                      "kannst (nicht mehr) die anderen Buttons bedienen.\n\n"

        elif select.values[0] == "restart":
            content = "🔄 Session neu starten\n\n" \
                      "Startet den Timer neu mit allen eingestellten Werten und \n" \
                      "setzt die aktuelle Session-Statistik zurück. (Wenn mehrere \n" \
                      "am Timer angemeldet sind, besprich das erst mit den anderen.)\n\n"

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

    def create_embed(self, name, status, working_time, break_time, end_of_phase, registered, voicy, sound, stats):
        color = disnake.Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else disnake.Colour.red()

        zeiten = f"{working_time} Minuten Arbeiten\n{break_time} Minuten Pause"
        delta = datetime.fromtimestamp(end_of_phase - time.time()).strftime("%M")
        remaining_value = f"{int(delta)+1} Minuten"
        endzeit = datetime.fromtimestamp(end_of_phase).strftime("%H:%M")
        end_value = f" [bis {endzeit} Uhr]" if status != "Beendet" else ""
        user_list = [self.bot.get_user(int(user_id)) for user_id in registered]
        angemeldet_value = ", ".join([user.mention for user in user_list])
        voicy_info = "🔊 Soundwiedergabe im Voicy" if voicy else "🔇 Kein Voicy-Beitritt"
        sound_info = f"🎶 {sound}" if voicy else "🎶 -"
        stats_info = " " if stats else " **nicht** "

        info_value = f"{voicy_info}\n" \
                     f"{sound_info}\n" \
                     f"📈 Session geht{stats_info}in die Statistik ein\n\n" \
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

    @commands.slash_command(description="Erstelle deine persönliche  Eieruhr")
    async def timer(self, interaction: ApplicationCommandInteraction):
        return

    @timer.sub_command()
    async def run(self, interaction: ApplicationCommandInteraction,
                        working_time: int = commands.Param(default=25, description="Länge der Lernphasen in Minuten (default: 25)"),
                        break_time: int = commands.Param(default=5, description="Länge der Pausenphasen in Minuten (default: 5)"),
                        name: str = commands.Param(default=None, description="Name/Titel des Timers"),
                        rounds: int = commands.Param(default=0, description="Anzahl der geplanten Lernphasen (default: 0 = manuell beenden)")):

        name = name if name else random.choice(self.default_names)
        end_of_phase = datetime.timestamp(datetime.now() + timedelta(minutes=working_time))
        status = "Arbeiten"
        registered = [str(interaction.author.id)]
        voicy = False
        sound = 'standard'
        into_global_stats = True
        session_stats = {'start': time.time(), 'rounds': 1}

        embed = self.create_embed(name, status, working_time, break_time, end_of_phase, registered, voicy, sound, into_global_stats)
        await interaction.response.send_message(embed=embed, view=self.get_view(voicy=voicy))
        message = await interaction.original_message()

        self.running_timers[str(message.id)] = {'name': name,
                                                'status': status,
                                                'working_time': working_time,
                                                'break_time': break_time,
                                                'end_of_phase': end_of_phase,
                                                'registered': registered,
                                                'channel': interaction.channel_id,
                                                'voicy': voicy,
                                                'sound': sound,
                                                'into_global_stats': into_global_stats,
                                                'session_stats': session_stats,
                                                'planned_rounds': rounds}
        self.save_running_timers()

    async def autocomp_stats_choices(inter: ApplicationCommandInteraction, user_input: str):
        stats_choices = ["day", "week", "month", "semester"]
        return [choice for choice in stats_choices if user_input.lower() in choice]

    @timer.sub_command()
    async def stats(self, interaction: ApplicationCommandInteraction,
                    period: str = commands.Param(autocomplete=autocomp_stats_choices,
                                                 description="day/week/month/semester")):
        # TODO
        await interaction.response.send_message(period, ephemeral=True)

    async def switch_phase(self, msg_id):
        if timer := self.running_timers.get(msg_id):
            if timer['status'] == "Arbeiten":
                if timer['planned_rounds'] == timer['session_stats']['rounds']:
                    self.running_timers.pop(msg_id)
                    self.save_running_timers()
                    return "Beendet"
                else:
                    timer['status'] = "Pause"
                    timer['end_of_phase'] = datetime.timestamp(datetime.now() + timedelta(minutes=timer['break_time']))
            elif timer['status'] == "Pause":
                timer['session_stats']['rounds'] += 1
                timer['status'] = "Arbeiten"
                timer['end_of_phase'] = datetime.timestamp(datetime.now() + timedelta(minutes=timer['working_time']))
            else:
                self.running_timers.pop(msg_id)
                self.save_running_timers()
                return "Beendet"
            self.save_running_timers()

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
            end_of_phase = timer['end_of_phase']
            registered = timer['registered']
            channel = timer['channel']
            voicy = timer['voicy']
            sound = timer['sound']
            into_global_stats = timer['into_global_stats']
            session_stats = timer['session_stats']
            return name, status, wt, bt, end_of_phase, registered, channel, voicy, sound, into_global_stats, session_stats

    async def edit_message(self, msg_id, mentions=None, create_new=True):
        if timer := self.running_timers.get(msg_id):
            channel_id = timer['channel']
            channel = await self.bot.fetch_channel(int(channel_id))
            try:
                msg = await channel.fetch_message(int(msg_id))

                name, status, wt, bt, end_of_phase, registered, _, voicy, sound, stats, _ = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, end_of_phase, registered, voicy, sound, stats)

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
                    self.save_running_timers()
                    msg = new_msg
                else:
                    await msg.edit(embed=embed, view=self.get_view(voicy=voicy))
                return str(msg.id)
            except disnake.errors.NotFound:
                self.running_timers.pop(msg_id)
                self.save_running_timers()
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
            if time.time() >= timer['end_of_phase']:
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

    @timer.error
    async def timer_error(self, ctx, error):
        await ctx.send("Das habe ich nicht verstanden. Die Timer-Syntax ist:\n"
                       "`/timer <learning-time?> <break-time?> <name?>`\n")

