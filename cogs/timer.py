import json
import os
import random
import time
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta

import disnake
from disnake import MessageInteraction, ApplicationCommandInteraction, TextInputStyle
from disnake.ext import commands, tasks
from disnake.ui import Select, TextInput

from views import timer_view

"""
  Environment Variablen:
  DISCORD_TIMER_FILE - json file mit allen aktuell laufenden timern
  DISCORD_TIMER_STATS_FILE - json file mit der Timer-Statistik

  Struktur der TIMER_FILE:
  {<msg_id>:{name:<Titel des Timers>, 
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
                             'rounds': <Anzahl der begonnenen Lernphasen>},
             planned_rounds: <Anzahl geplanter Lernphasen für automatisches Beenden oder 0 für manuelles Beenden>}}
           
  Neue Soundschemata lassen sich hinzufügen mittels neuem Ordner 'cogs/sounds/<schema>'
  in diesem müssen genau zwei Dateien sein: 'learning.mp3' und 'pause.mp3'
  
  Struktur der STATS_FILE:
  {<user_id>:{<day>:{time:<gelernte Zeit an dem Tag in Minuten>,
                     sessions:<Anzahl der Timersessions an dem Tag>}}}
  
"""

# TODO: weekly leaderboard

class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.timer_file_path = os.getenv("DISCORD_TIMER_FILE")
        self.stats_file_path = os.getenv("DISCORD_TIMER_STATS_FILE")
        self.default_names = ["Rapunzel", "Aschenputtel", "Schneewittchen", "Frau Holle", "Schneeweißchen und Rosenrot",
                              "Gestiefelter Kater", "Bremer Stadtmusikanten"]
        self.session_stat_messages = ["Fantastisch!", "Glückwunsch!", "Gut gemacht!", "Super!", "Spitze!", "Toll!",
                                      "Mega!", "Weiter so!"]
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
            name, status, wt, bt, end_of_phase, registered, _, voicy, sound, stats, session_stats, planned_rounds = self.get_details(msg_id)
            embed = self.create_embed(name, status, wt, bt, end_of_phase, registered, voicy, sound, stats,
                                      session_stats, planned_rounds)
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
                await interaction.response.defer()
                new_phase = await self.switch_phase(msg_id)
                if timer['voicy']:
                    if new_phase == "Pause":
                        await self.make_sound(registered, f"{timer['sound']}/pause.mp3")
                    if new_phase == "Arbeiten":
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
            if str(interaction.author.id) in timer['registered']:
                await interaction.response.defer()
                await self.stop_timer(msg_id)
            else:
                await interaction.response.send_message("Nur angemeldete Personen können den Timer beenden.\n"
                                                        "Klicke auf ⁉ für mehr Informationen.",
                                                        ephemeral=True)
        else:
            await interaction.response.send_message("Etwas ist schiefgelaufen...", ephemeral=True)

    async def stop_timer(self, msg_id):
        if timer := self.running_timers.get(msg_id):
            if timer['into_global_stats']:
                self.add_to_stats(timer['session_stats'], timer['registered'])
            registered = timer['registered']
            mentions = self.get_mentions(msg_id)
            timer['status'] = "Beendet"
            timer['registered'] = []

            if new_msg_id := await self.edit_message(msg_id, mentions=mentions):
                if timer['voicy']:
                    await self.make_sound(registered, 'applause.mp3')
                self.running_timers.pop(new_msg_id)
                self.save_running_timers()

    def add_to_stats(self, session_stats, user_ids):
        today = datetime.today().date().isoformat()
        for user_id in user_ids:
            if not self.stats.get(user_id):
                self.stats[user_id] = {}
            user_stats = self.stats.get(user_id)
            if not user_stats.get(today):
                user_stats[today] = {'time': 0, 'sessions': 0}
            user_stats_today = user_stats.get(today)
            user_stats_today['time'] += int((time.time() - session_stats['start'])/60)
            user_stats_today['sessions'] += 1
        self.save_stats()

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
                timer['into_global_stats'] = not timer['into_global_stats']
                await interaction.response.defer()
                await self.edit_message(msg_id, create_new=False)
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

    def create_embed(self, name, status, working_time, break_time, end_of_phase, registered, voicy, sound, stats, session_stats, planned_rounds):
        color = disnake.Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else disnake.Colour.red()

        zeiten = f"{working_time} Minuten Arbeiten\n{break_time} Minuten Pause"
        delta = int(end_of_phase - time.time())//60
        remaining_value = f"noch {int(delta)+1} Minuten" if status != 'Beendet' else "-"
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
                f"{remaining_value}\n\n" \

        embed = disnake.Embed(title=name,
                              description=descr,
                              color=color)

        if status != "Beendet":
            embed.add_field(name="Zeiten:", value=zeiten, inline=False)
            embed.add_field(name="Infos:", value=info_value, inline=False)
            embed.add_field(name="angemeldete User:", value=angemeldet_value if registered else "-", inline=False)
        else:
            end_title = random.choice(self.session_stat_messages)
            rounds = session_stats['rounds']
            pronoun = "Ihr habt" if len(registered) > 1 else "Du hast"
            if working_time == 25 and break_time == 5:
                end_info_start = f"{pronoun} **{rounds} Pomodor{'i' if rounds > 1 else 'o'}** geschafft.\n"
            else:
                minutes = int(time.time() - session_stats['start'])//60
                end_info_start = f"{pronoun} **{minutes} Minute{'n' if minutes!=1 else ''}** in **{rounds} " \
                                 f"Runde{'n' if rounds > 1 else ''}** gelernt.\n"
            end_info_end = f"Diese Timer-Session ging{stats_info}in die Statistik ein."
            embed.add_field(name=end_title, value=end_info_start + end_info_end, inline=False)

        round = session_stats['rounds']
        rounds = planned_rounds if planned_rounds != 0 else "∞"
        embed.set_footer(text=f"Runde {round}/{rounds}")

        return embed

    @commands.slash_command()
    async def timer(self, interaction: ApplicationCommandInteraction):
        return

    @timer.sub_command(description="Erstelle deine persönliche  Eieruhr")
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
        planned_rounds = rounds

        embed = self.create_embed(name, status, working_time, break_time, end_of_phase, registered, voicy, sound,
                                  into_global_stats, session_stats, planned_rounds)
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
                                                'planned_rounds': planned_rounds}
        self.save_running_timers()

    async def autocomp_stats_choices(inter: ApplicationCommandInteraction, user_input: str):
        stats_choices = ["day", "week", "month", "semester", "all"]
        return [choice for choice in stats_choices if user_input.lower() in choice]

    @timer.sub_command(description="Lass dir deine Statistik zur Timernutzung ausgeben.")
    async def stats(self, interaction: ApplicationCommandInteraction,
                    period: str = commands.Param(autocomplete=autocomp_stats_choices,
                                                 description="day/week/month/semester/all")):
        if period == "edit":
            await self.edit_stats(interaction)

        else:
            if period in ['day', 'week', 'month', 'semester', 'all']:
                if user_stats := self.stats.get(str(interaction.author.id)):
                    period_text = ""
                    sum_learning_time, sum_sessions = 0, 0
                    today = datetime.today().date()
                    today_iso = today.isoformat()

                    if period == 'day':
                        period_text = "heute"
                        if today_stats := user_stats.get(today_iso):
                            sum_learning_time = today_stats['time']
                            sum_sessions = today_stats['sessions']

                    elif period == 'week':
                        period_text = "diese Woche"
                        weekday = today.weekday()
                        monday = today - timedelta(days=weekday)
                        monday_iso = monday.isoformat()

                        for (date, data) in user_stats.items():
                            if monday_iso >= date >= today_iso:
                                sum_learning_time += data['time']
                                sum_sessions += data['sessions']

                    elif period == 'month':
                        period_text = "diesen Monat"
                        month = today.month
                        for (date, data) in user_stats.items():
                            if datetime.fromisoformat(date).month == month:
                                sum_learning_time += data['time']
                                sum_sessions += data['sessions']

                    elif period == 'semester':
                        period_text = "in diesem Semester"
                        # Semester von 1.4.-30.9. bzw 1.10.-31.3.
                        year = today.year
                        month = today.month

                        if 4 <= month <= 9: #Sommersemester
                            sem_start = f'{year}-04-01'
                        else: #Wintersemester
                            year = year if (10 <= month <= 12) else (year-1)
                            sem_start = f'{year}-10-01'

                        for (date, data) in user_stats.items():
                            if date >= sem_start:
                                sum_learning_time += data['time']
                                sum_sessions += data['sessions']

                    elif period == 'all':
                        first_session = today_iso
                        for (date, data) in user_stats.items():
                            if date < first_session:
                                first_session = date
                            sum_learning_time += data['time']
                            sum_sessions += data['sessions']
                        first_session_date = datetime.fromisoformat(first_session).strftime("%d.%m.%y")
                        period_text = f"seit dem {first_session_date}"

                    if sum_learning_time > 0 or sum_sessions > 0:
                        await interaction.response.send_message(
                            f"Du hast {period_text} schon **{sum_learning_time} Minute{'n' if sum_learning_time > 1 else ''}** in"
                            f" **{sum_sessions} Session{'s' if sum_sessions > 1 else ''}** gelernt. "
                            f"{random.choice(self.session_stat_messages)}", ephemeral=True)
                    else:
                        await interaction.response.send_message(
                            f"Für {period_text} ist keine Statistik von dir vorhanden. Nutze den Timer mit `/timer run`"
                            f" oder gib einen anderen Zeitraum an.", ephemeral=True)
                else:
                    await interaction.response.send_message("Von dir sind noch keine Einträge in der Statistik.\n"
                                                            "Benutze den Timer mit dem Kommando `/timer run` zum Lernen"
                                                            " und lass dir dann hier deine Erfolge anzeigen.",
                                                            ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Bitte gib für den Zeitraum `day`, `week`, `month`, `semester` oder `all` an.", ephemeral=True)

    async def edit_stats(self, interaction: ApplicationCommandInteraction):
        author_roles = [role.id for role in interaction.author.roles]
        if int(os.getenv('DISCORD_MOD_ROLE')) not in author_roles:
            await interaction.response.send_message("Glückwunsch, du hast die geheime Statistik-Manipulations-Funktion "
                                                    "entdeckt. Zu deinem Pech ist sie nur von Mods nutzbar. Muss an deiner"
                                                    "Statistik etwas verändert werden, wende dich bitte an eine "
                                                    "Moderatorin.", ephemeral=True)
        else:
            user_id_list = [int(user_id) for user_id in self.stats.keys()]
            user_name_list = [self.bot.get_user(user_id).display_name for user_id in user_id_list]
            view = timer_view.EditSelectView(self.on_edit_user_select, user_id_list, user_name_list)
            await interaction.response.send_message("Wähle hier die Userin aus, deren Statistik du bearbeiten willst.",
                                                    view=view, ephemeral=True)

    async def on_edit_user_select(self, select: Select, interaction: MessageInteraction):
        user_id = str(select.values[0])
        user_name = self.bot.get_user(int(user_id)).display_name
        dates = [date for date in self.stats.get(user_id).keys()]
        view = timer_view.EditSelectView(self.on_edit_date_select, dates, dates, further_info=user_id)
        await interaction.response.edit_message(content=f"Ändere die Statistik von **{user_name}**:\n\n"
                                                f"Wähle hier das Datum aus, dessen Statistik du bearbeiten willst.",
                                                view=view)

    async def on_edit_date_select(self, select: Select, interaction: MessageInteraction, user_id):
        user_name = self.bot.get_user(int(user_id)).display_name
        date = select.values[0]
        stats = self.stats.get(user_id).get(date)

        time_input = TextInput(label="Gelernte Zeit in Minuten:",
                               placeholder=f"{stats['time']}",
                               custom_id="timer:edit:time",
                               style=TextInputStyle.short,
                               max_length=3)

        sessions_input = TextInput(label="Anzahl der Sessions:",
                                   placeholder=f"{stats['sessions']}",
                                   custom_id="timer:edit:sessions",
                                   style=TextInputStyle.short,
                                   max_length=1)

        await interaction.response.send_modal(
            title=f"Ändere die Statistik vom {date} für {user_name}",
            custom_id="timer:edit:modal",
            components=[time_input, sessions_input],
        )
        #await interaction.response.edit_message(content=f"{stats['time']}, {stats['sessions']}")

    async def switch_phase(self, msg_id):
        if timer := self.running_timers.get(msg_id):
            if timer['status'] == "Arbeiten":
                if (timer['session_stats']['rounds'] >= timer['planned_rounds']) and (timer['planned_rounds'] != 0):
                    await self.stop_timer(msg_id)
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
            planned_rounds = timer['planned_rounds']
            return name, status, wt, bt, end_of_phase, registered, channel, voicy, sound, into_global_stats, \
                   session_stats, planned_rounds

    async def edit_message(self, msg_id, mentions=None, create_new=True):
        if timer := self.running_timers.get(msg_id):
            channel_id = timer['channel']
            channel = await self.bot.fetch_channel(int(channel_id))
            try:
                msg = await channel.fetch_message(int(msg_id))

                name, status, wt, bt, end_of_phase, registered, _, voicy, sound, stats, session_stats, planned_rounds = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, end_of_phase, registered, voicy, sound, stats,
                                          session_stats, planned_rounds)

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
        await ctx.send("Das habe ich nicht verstanden. Benutze `/timer run` um einen Timer zu starten oder"
                       "`/timer stats` um dir deine Nutzungsstatistik ausgeben zu lassen.")
