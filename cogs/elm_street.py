import json
import os
from asyncio import sleep
from copy import deepcopy
from random import SystemRandom
from typing import Union

import disnake
from disnake import ApplicationCommandInteraction, ButtonStyle
from disnake.ext import commands, tasks
from dotenv import load_dotenv

from utils import send_dm

load_dotenv()


def get_player_from_embed(embed: disnake.Embed):
    return embed.description.split()[0].strip("<@!>")


def calculate_sweets(event):
    sweets_min = event.get("sweets_min")
    sweets_max = event.get("sweets_max")

    if sweets_min and sweets_max:
        return SystemRandom().randint(sweets_min, sweets_max)

    return None


def calculate_courage(event):
    courage_min = event.get("courage_min")
    courage_max = event.get("courage_max")

    if courage_min and courage_max:
        return SystemRandom().randint(courage_min, courage_max)

    return None


ShowOption = commands.option_enum(["10", "all"])


def get_doors_visited(group):
    if doors_visited := group.get("doors_visited"):
        return doors_visited
    else:
        doors_visited = []
        group["doors_visited"] = doors_visited
        return doors_visited


class ElmStreet(commands.Cog):
    def __init__(self, bot):

        self.max_courage = 100
        self.min_courage = 20
        self.min_group_courage = 20

        self.inc_courage_step = 10

        self.bot = bot
        self.groups = {}
        self.players = {}
        self.story = {}
        self.load()
        self.elm_street_channel_id = int(os.getenv("DISCORD_ELM_STREET_CHANNEL"))
        self.halloween_category_id = int(os.getenv("DISCORD_HALLOWEEN_CATEGORY"))
        self.bot.view_manager.register("on_join", self.on_join)
        self.bot.view_manager.register("on_joined", self.on_joined)
        self.bot.view_manager.register("on_start", self.on_start)
        self.bot.view_manager.register("on_stop", self.on_stop)
        self.bot.view_manager.register("on_story", self.on_story)
        self.bot.view_manager.register("on_leave", self.on_leave)

        self.increase_courage.start()

    def load(self):
        with open("data/elm_street_groups.json", "r") as groups_file:
            self.groups = json.load(groups_file)
        with open("data/elm_street_players.json", "r") as players_file:
            self.players = json.load(players_file)
        with open("data/elm_street_story.json", "r") as story_file:
            self.story = json.load(story_file)

    def save(self):
        with open("data/elm_street_groups.json", "w") as groups_file:
            json.dump(self.groups, groups_file)
        with open("data/elm_street_players.json", "w") as players_file:
            json.dump(self.players, players_file)

    @commands.slash_command(name="leaderboard",
                            description="Zeigt das Leaderboard der Elm Street Sammlerinnen-Gemeinschaft an.",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_leaderboard(self, interaction: ApplicationCommandInteraction, show: ShowOption = "10"):
        embed = await self.leaderboard(all=show)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="group-stats",
                            description="Zeigt die aktuelle Gruppenstatistik an.",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_group_stats(self, interaction: ApplicationCommandInteraction):
        thread_id = interaction.channel_id
        if str(thread_id) in self.groups.keys():
            embed = await self.get_group_stats_embed(interaction.channel_id)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Gruppenstatistiken können nur in Gruppenthreads ausgegeben werden."
                                                    , ephemeral=True)

    @commands.slash_command(name="leave-group",
                            description="Hiermit verlässt du deine aktuelle Gruppe",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_leave_group(self, interaction: ApplicationCommandInteraction):
        thread_id = interaction.channel_id
        player_id = interaction.author.id
        if group := self.groups.get(str(thread_id)):
            if not player_id == group['owner']:
                if player_id in group.get('players'):
                    self.leave_group(thread_id, player_id)
                    await interaction.response.send_message(f"<@{player_id}> hat die Gruppe verlassen.")
                else:
                    await interaction.response.send_message(
                        "Du bist garnicht Teil dieser Gruppe.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Du darfst deine Gruppe nicht im Stich lassen. Als Gruppenleiterin kannst du sie höchstens beenden, "
                    "aber nicht verlassen.", ephemeral=True)
        else:
            await interaction.response.send_message("Dieses Kommando kann nur in einem Gruppenthread ausgeführt werden."
                                                    , ephemeral=True)

    @commands.slash_command(name="stats",
                            description="Zeigt deine persönliche Statistik an.",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_stats(self, interaction: ApplicationCommandInteraction):
        embed = self.get_personal_stats_embed(interaction.author.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="start-group",
                            description="Erstelle eine Gruppe für einen Streifzug durch die Elm Street",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_start_group(self, interaction: ApplicationCommandInteraction, name: str):
        author = interaction.author
        category = await self.bot.fetch_channel(self.halloween_category_id)
        channel = await self.bot.fetch_channel(self.elm_street_channel_id)
        channel_type = None if self.bot.is_prod() else disnake.ChannelType.public_thread

        player = self.get_player(author)

        if interaction.channel == channel:
            if self.can_play(player):
                if not self.is_playing(author.id):
                    if player["courage"] >= 50:
                        thread = await channel.create_thread(name=name, auto_archive_duration=1440, type=channel_type)
                        voice_channel = await category.create_voice_channel(name)
                        await voice_channel.set_permissions(interaction.author, view_channel=True, connect=True)

                        await thread.send(
                            f"Hallo {author.mention}. Der Streifzug deiner Gruppe durch die Elm-Street findet "
                            f"in diesem Thread statt. Sobald deine Gruppe sich zusammen gefunden hat, kannst "
                            f"du über einen Klick auf den Start Button eure Reise starten.\n\n"
                            f"Für das volle Gruselerlebnis könnt ihr euch während des Abenteuers gegenseitig "
                            f"Schauermärchen in eurem Voice Channel {voice_channel.mention} erzählen.",
                            view=self.get_start_view())

                        await interaction.response.send_message(self.get_invite_message(author),
                                                                view=self.get_join_view(thread.id))

                        message = await interaction.original_message()
                        self.groups[str(thread.id)] = {"message": message.id, "players": [author.id],
                                                       "owner": author.id,
                                                       "requests": [], 'stats': {'sweets': 0, 'courage': 0, 'doors': 0},
                                                       "voice_channel": voice_channel.id}
                        self.save()
                    else:
                        await interaction.response.send_message(
                            "Du fühlst dich derzeit noch nicht mutig genug, um aus Süßigkeitenjagd zu gehen. Warte, bis deine Mutpunkte wieder mindestens 50 betragen. Den aktuellen Stand deiner Mutpunkte kannst du über /stats prüfen.",
                            ephemeral=True)
                else:
                    await interaction.response.send_message(
                        "Es tut mir leid, aber du kannst nicht an mehr als einer Jagd gleichzeitig teilnehmen. "
                        "Beende erst das bisherige Abenteuer, bevor du dich einer neuen Gruppe anschließen kannst.",
                        ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Du zitterst noch zu sehr von deiner letzten Runde. Ruh dich noch ein wenig aus bevor du weiter spielst.",
                    ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Gruppen können nur in <#{self.elm_street_channel_id}> gestartet werden.",
                ephemeral=True)

    async def on_join(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        player = self.get_player(interaction.author)

        try:
            if group := self.groups.get(str(value)):
                requests = [r['player'] for r in group.get('requests')]
                if interaction.author.id not in requests:
                    if self.can_play(player):
                        if not self.is_already_in_this_group(interaction.author.id, interaction.message.id):
                            if not self.is_playing(interaction.author.id):
                                if player["courage"] >= 50:
                                    thread = await self.bot.fetch_channel(value)
                                    msg = await self.bot.view_manager.confirm(thread, "Neuer Rekrut",
                                                                              f"{interaction.author.mention} würde sich gerne der Gruppe anschließen.",
                                                                              fields=[{'name': 'aktuelle Mutpunkte',
                                                                                       'value': self.get_courage_message(
                                                                                           player)}],
                                                                              custom_prefix="rekrut",
                                                                              callback_key="on_joined")
                                    player.get('messages').append({'id': msg.id, 'channel': thread.id})
                                    group.get('requests').append({'player': interaction.author.id, 'id': msg.id})
                                    self.save()
                                else:
                                    await interaction.response.send_message(
                                        "Du fühlst dich derzeit noch nicht mutig genug, um aus Süßigkeitenjagd zu gehen. Warte, bis deine Mutpunkte wieder mindestens 50 betragen. Den aktuellen Stand deiner Mutpunkte kannst du über /stats prüfen.",
                                        ephemeral=True)
                            else:
                                await interaction.response.send_message(
                                    "Es tut mir leid, aber du kannst nicht an mehr als einer Jagd gleichzeitig teilnehmen. "
                                    "Beende erst das bisherige Abenteuer, bevor du dich einer neuen Gruppe anschließen kannst.",
                                    ephemeral=True)
                        else:
                            await interaction.response.send_message(
                                "Du bist schon Teil dieser Gruppe! Schau doch mal in eurem "
                                "Thread vorbei.", ephemeral=True)
                    else:
                        await interaction.response.send_message(
                            "Du zitterst noch zu sehr von deiner letzten Runde. Ruh dich noch ein wenig aus bevor du weiter spielst.",
                            ephemeral=True)
                else:
                    await interaction.response.send_message(
                        "Für diese Gruppe hast du dich schon beworben. Warte auf eine Entscheidung des Gruppenleiters.",
                        ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                "Ein Fehler ist aufgetreten. Überprüfe bitte, ob du der richtigen Gruppe beitreten wolltest. "
                "Sollte der Fehler erneut auftreten, sende mir (Boty McBotface) bitte eine Direktnachricht.",
                ephemeral=True)

        if not interaction.response.is_done():
            await interaction.response.send_message("Dein Wunsch, der Gruppe beizutreten wurde weitergeleitet.",
                                                    ephemeral=True)

    async def on_joined(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        player_id = int(get_player_from_embed(interaction.message.embeds[0]))
        thread_id = interaction.channel_id
        owner_id = self.groups.get(str(thread_id)).get('owner')

        if interaction.author.id == owner_id:
            if group := self.groups.get(str(interaction.channel_id)):
                if value:
                    if not self.is_playing(player_id):
                        group["players"].append(player_id)

                        # Request-Nachrichten aus allen Threads und aus players löschen
                        for thread_id in self.groups:
                            requests = self.groups.get(str(thread_id)).get('requests')
                            for request in requests:
                                if request['player'] == player_id:
                                    thread = await self.bot.fetch_channel(int(thread_id))
                                    message = await thread.fetch_message(request['id'])
                                    player = await self.bot.fetch_user(player_id)
                                    voice_channel = await self.bot.fetch_channel(group["voice_channel"])
                                    await voice_channel.set_permissions(player, view_channel=True, connect=True)
                                    await message.delete()
                                    self.delete_message_from_player(player_id, request['id'])
                                    requests.remove(request)

                        await interaction.message.channel.send(
                            f"<@!{player_id}> ist jetzt Teil der Crew! Herzlich willkommen.",
                            view=self.get_leave_view())
                        self.save()
                else:
                    await self.deny_join_request(group, interaction.message, player_id)
        else:
            await interaction.response.send_message("Nur die Gruppenerstellerin kann User annehmen oder ablehnen.",
                                                    ephemeral=True)

    async def on_start(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        thread_id = interaction.channel_id
        owner_id = self.groups.get(str(thread_id)).get('owner')
        if interaction.author.id == owner_id:
            if group := self.groups.get(str(interaction.channel.id)):

                elm_street_channel = await self.bot.fetch_channel(self.elm_street_channel_id)
                group_message = await elm_street_channel.fetch_message(group["message"])
                await group_message.delete()
                await interaction.message.edit(view=self.get_start_view(disabled=True))

                if value:  # auf Start geklickt
                    await self.deny_open_join_requests(thread_id, group)
                    random_player = await self.bot.fetch_user(SystemRandom().choice(group.get('players')))
                    bags = ["einen Putzeimer, der", "eine Plastiktüte von Aldi, die", "einen Einhorn-Rucksack, der",
                            "eine Reisetasche, die", "eine Wickeltasche mit zweifelhaftem Inhalt, die",
                            "einen Rucksack, der", "eine alte Holzkiste, die", "einen Leinensack, der",
                            "einen Müllsack, der", "einen Jutebeutel mit verwaschener gotischer Schrift, die",
                            "eine blaue Ikea-Tasche, die"]
                    await interaction.response.send_message(
                        f"```\nSeid ihr bereit? Taschenlampe am Gürtel, Schminke im Gesicht? Dann kann es losgehen!\n"
                        f"Doch als ihr gerade in euer Abenteuer starten wollt, fällt {random_player.name} auf, dass ihr euch erst noch Behälter für die erwarteten Süßigkeiten suchen müsst. \nIhr schnappt euch also {SystemRandom().choice(bags)} gerade da ist. \nNun aber los!\n```")
                    await self.on_story(button, interaction, "doors")
                else:  # auf Abbrechen geklickt
                    # voice channel löschen
                    voice_channel_id = self.groups[str(thread_id)]["voice_channel"]
                    voice_channel = await self.bot.fetch_channel(voice_channel_id)
                    if len(voice_channel.members) == 0:
                        await voice_channel.delete()

                    self.groups.pop(str(thread_id))
                    self.save()
                    await interaction.response.send_message(f"Du hast die Runde abgebrochen. Dieser Thread wurde "
                                                            f"archiviert und du kannst in <#{self.elm_street_channel_id}>"
                                                            f" eine neue Runde starten.", ephemeral=True)
                    await interaction.channel.send(f"Dieses Abenteuer ist beendet und zum Nachlesen archiviert."
                                                   f"\nFür mehr Halloween-Spaß, schau in <#{self.elm_street_channel_id}>"
                                                   f"vorbei")
                    await interaction.channel.edit(archived=True)
        else:
            await interaction.response.send_message(
                "Nur die Gruppenerstellerin kann die Gruppe starten lassen oder die "
                "Tour abbrechen.",
                ephemeral=True)

    async def on_stop(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        thread_id = interaction.channel_id

        # Button disablen
        await interaction.message.edit(view=self.get_stop_view(disabled=True))

        # Gruppenstatistik in elm-street posten
        stats_embed = await self.get_group_stats_embed(thread_id)
        elm_street = await self.bot.fetch_channel(self.elm_street_channel_id)
        await elm_street.send("", embed=stats_embed)

        # jedem Spieler seine Süßigkeiten geben
        sweets = self.groups.get(str(thread_id)).get('stats').get('sweets')
        self.share_sweets(sweets, thread_id)

        # aktuelles leaderboard in elm-street posten
        leaderboard_embed = await self.leaderboard(all="all")
        await elm_street.send("", embed=leaderboard_embed)

        # voice channel löschen
        voice_channel_id = self.groups[str(thread_id)]["voice_channel"]
        voice_channel = await self.bot.fetch_channel(voice_channel_id)
        if len(voice_channel.members) == 0:
            await voice_channel.delete()

        # Gruppe aus json löschen
        self.groups.pop(str(thread_id))
        self.save()

        # Thread archivieren
        await interaction.channel.send(f"Dieses Abenteuer ist beendet und zum Nachlesen archiviert."
                                       f"\nFür mehr Halloween-Spaß, schau in <#{self.elm_street_channel_id}>"
                                       f"vorbei")
        await interaction.channel.edit(archived=True)

    async def on_story(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        thread_id = interaction.channel_id
        group = self.groups.get(str(thread_id))
        owner_id = group.get('owner')
        if interaction.author.id == owner_id:
            if value == "stop":
                await self.on_stop(button, interaction, value)

            elif not self.can_proceed_story(interaction.channel_id):
                value = "fear"

            if events := self.story.get("events"):
                if value == "knock_on_door":
                    group = self.groups.get(str(thread_id))
                    group_stats = group.get('stats')
                    group_stats['doors'] += 1
                    self.save()

                if event := events.get(value):
                    channel = interaction.message.channel
                    choice = self.get_choice(value, event, group)
                    if not choice:
                        view = self.get_story_view("fear")
                        await channel.send("```\nAls ihr euch auf den Weg zur nächsten Tür macht, seht ihr am Horizont "
                                           "langsam die Sonne aufgehen. Ihr betrachtet eure Beute und beschließt, "
                                           "für dieses Jahr die Jagd zu beenden und tretet den Heimweg an.\n```",
                                           view=view)
                        await interaction.message.delete()
                    else:
                        text = choice["text"]
                        view = self.get_story_view(choice.get("view"))
                        sweets = calculate_sweets(choice)
                        courage = calculate_courage(choice)
                        text = self.apply_sweets_and_courage(text, sweets, courage, interaction.channel_id)
                        await channel.send(f"```\n{text}\n```")
                        if view:
                            await channel.send("Was wollt ihr als nächstes tun?", view=view)
                        if next := choice.get("next"):
                            await self.on_story(button, interaction, next)
                        else:
                            await interaction.message.delete()
        else:
            await interaction.response.send_message("Nur die Gruppenleiterin kann die Gruppe steuern.",
                                                    ephemeral=True)

    async def on_leave(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        thread_id = interaction.channel_id
        player_id = interaction.author.id
        msg_player = interaction.message.mentions[0]

        if msg_player.id == player_id:
            self.leave_group(thread_id, player_id)
            await interaction.response.send_message(f"<@{player_id}> hat die Gruppe verlassen.")
            await interaction.message.edit(view=self.get_leave_view(disabled=True))
        else:
            await interaction.response.send_message(
                f"Nur <@{player_id}> darf diesen Button bedienen. Wenn du die Gruppe "
                f"verlassen willst, versuche es mit `/leave-group`", ephemeral=True)

    def get_choice(self, key, event, group):
        if key == "doors":
            doors_visited = get_doors_visited(group)
            r = list(range(0, len(event) - 1))
            for door_visited in doors_visited:
                r.remove(door_visited)

            if len(r) == 0:
                return None

            i = SystemRandom().choice(r)
            doors_visited.append(i)
            self.save()
            return event[i]
        else:
            return SystemRandom().choice(event)

    def get_story_view(self, view_name: str):
        if views := self.story.get("views"):
            if buttons := views.get(view_name):
                return self.bot.view_manager.view(deepcopy(buttons), "on_story")

        return None

    def get_join_view(self, group_id: int):
        buttons = [
            {"label": "Join", "style": ButtonStyle.green, "value": group_id, "custom_id": "elm_street:join"}
        ]
        return self.bot.view_manager.view(buttons, "on_join")

    def get_start_view(self, disabled=False):
        buttons = [
            {"label": "Start", "style": ButtonStyle.green, "value": True, "custom_id": "elm_street:start",
             "disabled": disabled},
            {"label": "Abbrechen", "style": ButtonStyle.gray, "value": False, "custom_id": "elm_street:cancel",
             "disabled": disabled}
        ]
        return self.bot.view_manager.view(buttons, "on_start")

    def get_stop_view(self, disabled=False):
        buttons = [
            {"label": "Beendet", "style": ButtonStyle.red, "custom_id": "elm_street:stop", "disabled": disabled}
        ]
        return self.bot.view_manager.view(buttons, "on_stop")

    def get_leave_view(self, disabled=False):
        buttons = [
            {"label": "Verlassen", "style": ButtonStyle.gray, "custom_id": "elm_street:leave", "disabled": disabled}
        ]
        return self.bot.view_manager.view(buttons, "on_leave")

    def is_playing(self, user_id: int = None):
        for group in self.groups.values():
            if players := group.get("players"):
                if user_id in players:
                    return True
        return False

    def is_already_in_this_group(self, user_id, message_id):
        for group in self.groups.values():
            if message_id == group.get('message'):
                if user_id in group.get('players'):
                    return True
        return False

    def can_proceed_story(self, thread_id):
        group = self.groups.get(str(thread_id))

        player_ids = group.get("players")
        num_players = 0
        group_courage = 0

        for player_id in player_ids:
            player = self.players.get(str(player_id))
            num_players += 1
            group_courage += player["courage"]
        average_courage = group_courage / num_players

        return self.min_group_courage < average_courage

    def can_play(self, player):
        if player.get('courage') < self.min_courage:
            return False
        return True

    def get_player(self, user: Union[disnake.User, disnake.Member]):
        if player := self.players.get(str(user.id)):
            return player
        else:
            player = {"courage": self.max_courage, "sweets": 0, "messages": []}
            self.players[str(user.id)] = player
            self.save()
            return player

    def get_courage_message(self, player):
        courage = player.get('courage')
        message = f"{courage}"
        return message

    def delete_message_from_player(self, player_id, message_id):
        if player := self.players.get(str(player_id)):
            messages = player.get('messages')
            for msg in messages:
                if msg['id'] == message_id:
                    messages.remove(msg)
                    self.save()

    async def leaderboard(self, all: ShowOption = 10, interaction: ApplicationCommandInteraction = None):
        places = scores = "\u200b"
        place = 0
        max = 0 if all == "all" else 10
        ready = False
        embed = disnake.Embed(title="Elm-Street Leaderboard",
                              description="Wie süß bist du wirklich??\n" +
                                          (":jack_o_lantern: " * 8))
        last_score = -1
        for player_id, player_data in sorted(self.players.items(), key=lambda item: item[1]["sweets"], reverse=True):
            value = player_data["sweets"]
            # embed.set_thumbnail(
            #     url="https://www.planet-wissen.de/kultur/religion/ostern/tempxostereiergjpg100~_v-gseagaleriexl.jpg")
            elm_street_channel = await self.bot.fetch_channel(self.elm_street_channel_id)
            try:
                if last_score != value:
                    place += 1
                last_score = value
                if 0 < max < place:
                    if ready:
                        break
                    # elif str(ctx.author.id) != player_id:
                    #    continue
                places += f"{place}: <@!{player_id}>\n"
                scores += f"{value:,}\n".replace(",", ".")

                # if str(ctx.author.id) == player_id:
                #    ready = True
            except:
                pass

        embed.add_field(name=f"Sammlerin", value=places)
        embed.add_field(name=f"Süßigkeiten", value=scores)
        return embed
        # await elm_street_channel.send("", embed=embed)

    async def get_group_stats_embed(self, thread_id):
        thread = await self.bot.fetch_channel(thread_id)
        players = self.groups.get(str(thread_id)).get('players')
        stats = self.groups.get(str(thread_id)).get('stats')

        players_value = ', '.join([f'<@{int(player)}>' for player in players])
        doors_value = stats.get('doors')
        sweets_value = stats.get('sweets')
        courage_value = stats.get('courage')

        embed = disnake.Embed(title=f'Erfolge der Gruppe "{thread.name}"')
        embed.add_field(name='Mitspieler', value=players_value, inline=False)
        embed.add_field(name="Besuchte Türen", value=doors_value)
        embed.add_field(name="Gesammelte Süßigkeiten", value=sweets_value)
        embed.add_field(name="Verlorene Mutpunkte", value=courage_value)

        return embed

    def get_personal_stats_embed(self, player_id):
        player = self.players.get(str(player_id))
        embed = disnake.Embed(title="Deine persönlichen Erfolge")
        embed.add_field(name="Süßigkeiten", value=player['sweets'])
        embed.add_field(name="Mutpunkte", value=player['courage'])
        return embed

    def get_invite_message(self, author):
        texts = [f"Du bist mitten in einer Großstadt gelandet.\n"
                 f"Der leise Wind weht Papier die Straße lang. "
                 f"Ansonsten hörst du nur in der Ferne das Geräusch vorbeifahrender Autos.\n"
                 f"Da, was war das?\n"
                 f"Hat sich da nicht etwas bewegt?\n"
                 f"Ein Schatten an der Mauer?\n"
                 f"Ein Geräusch wie von Krallen auf Asphalt.\n"
                 f"Du drehst dich im Kreis.\n"
                 f"Ein leises Lachen in deinem Rücken.\n"
                 f"Und da, gerade außerhalb deines Sichtfeldes eine Tür die sich quietschend öffnet.\n"
                 f"Eine laute Stimme ruft fragend: \"Ich zieh los um die Häuser, wäre ja gelacht wenn nur Kinder heute "
                 f"abend Süßkram bekommen. Wer ist mit dabei?\"\n"
                 f"Du drehst dich zur Tür und siehst {author.mention}s entschlossenen Gesichtsausdruck.",
                 f"Eine Einladung über die Sozialen Netzwerke hat dich Aufmerksam werden lassen. \n"
                 f"Darin war von einer großen Halloween Party die Rede, "
                 f"als Treffpunkt war ein Park in der Innenstadt angegeben.\n"
                 f"Schon beim eintreffen merkst du, dass es keine angemeldete Party ist: "
                 f"überall ist Blaulicht und du siehst einige Polizeiwagen.\n"
                 f"Du entscheidest dich die Pläne für den Abend noch mal zu überdenken. "
                 f"Aber was tun? \n"
                 f"Deine Verkleidung ist zu aufwendig um schon wieder nach Hause zu gehen.\n"
                 f"In deiner Nähe stehen noch andere Menschen in Verkleidung die nicht wissen was sie mit dem angebrochenen Abend anfangen sollen. "
                 f"Da fragt {author.mention} laut in die Runde: \"Wer hat Lust um die Häuser zu ziehen und gemeinsam Süßigkeiten zu sammeln?\""
                 ]

        return SystemRandom().choice(texts)

    def get_group_by_voice_id(self, voice_id):
        for group in self.groups.values():
            if vc := group.get("voice_channel"):
                if vc == voice_id:
                    return group

        return None

    def apply_sweets_and_courage(self, text, sweets, courage, thread_id):
        group = self.groups.get(str(thread_id))
        player_ids = group.get("players")
        group_stats = group.get('stats')

        if sweets:
            if sweets > 0:
                text += f"\n\nIhr erhaltet jeweils {sweets} Süßigkeiten."
            if sweets == 0:
                text += f"\n\nIhr habt genau so viele Süßigkeiten wie vorher."
            if sweets < 0:
                text += f"\n\nIhr verliert jeweils {sweets} Süßigkeiten."
            group_stats['sweets'] += sweets
        if courage:
            if courage > 0:
                text += f"\n\nIhr verliert jeweils {courage} Mutpunkte."
            for player_id in player_ids:
                player = self.players.get(str(player_id))
                player["courage"] -= courage
            group_stats['courage'] += courage

        self.save()
        # TODO Was passiert wenn die courage eines Players zu weit sinkt?
        return text

    def share_sweets(self, sweets, thread_id):
        group = self.groups.get(str(thread_id))
        player_ids = group.get("players")
        for player_id in player_ids:
            player = self.players.get(str(player_id))
            player["sweets"] += sweets

    def leave_group(self, thread_id, player_id):
        group = self.groups.get(str(thread_id))
        group_players = group.get('players')
        player = self.players.get(str(player_id))

        # Spieler auszahlen
        group_stats = group.get('stats')
        player["sweets"] += group_stats['sweets']

        # Spieler aus Gruppe löschen
        group_players.remove(player_id)
        self.save()

    async def deny_join_request(self, group, message, player_id):
        user = self.bot.get_user(player_id)
        outfit = ["Piraten", "Einhörner", "Geister", "Katzen", "Weihnachtswichtel"]
        dresscode = ["Werwölfe", "Vampire", "Alice im Wunderland", "Hexen", "Zombies"]
        texts = [
            "Wir wollen um die Häuser ziehen und Kinder erschrecken. Du schaust aus, als würdest du den "
            "Kindern lieber unsere Süßigkeiten geben. Versuch es woanders.",
            f"Ich glaub du hast dich verlaufen, in dieser Gruppe können wir keine "
            f"{SystemRandom().choice(outfit)} gebrauchen. Unser Dresscode ist: {SystemRandom().choice(dresscode)}."]
        await send_dm(user, SystemRandom().choice(texts))
        group["requests"].remove({'player': player_id, 'id': message.id})
        self.save()
        # Request Nachricht aus diesem Thread und aus players löschen
        self.delete_message_from_player(player_id, message.id)
        await message.delete()

    async def deny_open_join_requests(self, thread_id, group):
        thread = await self.bot.fetch_channel(thread_id)

        if requests := group.get("requests"):
            for request in requests:
                message = await thread.fetch_message(request["id"])
                await self.deny_join_request(group, message, request["player"])

    @tasks.loop(minutes=5)
    async def increase_courage(self):
        actual_playing = []
        for p in (self.groups.get(group).get('players') for group in self.groups):
            actual_playing += p
        # pro Spieler: courage erhöhen
        for player in self.players:
            # nur wenn Spieler nicht gerade spielt
            if int(player) not in actual_playing:
                player = self.players.get(player)
                courage = player.get('courage')
                if courage < self.max_courage:
                    courage += self.inc_courage_step
                    player['courage'] = courage if courage < self.max_courage else self.max_courage
                    self.save()

                    # pro Nachricht: Nachricht erneuern
                    if messages := player.get('messages'):
                        for message in messages:
                            channel = await self.bot.fetch_channel(message['channel'])
                            msg = await channel.fetch_message(message['id'])
                            embed = msg.embeds[0]
                            embed.clear_fields()
                            embed.add_field(name='aktuelle Mutpunkte', value=self.get_courage_message(player))
                            await msg.edit(embed=embed)

    @increase_courage.before_loop
    async def before_increase(self):
        await sleep(10)

    @commands.Cog.listener(name="on_voice_state_update")
    async def voice_state_changed(self, member, before, after):
        if not after.channel:
            voice_channel_left = before.channel
            if len(voice_channel_left.members) == 0 and \
                    voice_channel_left.category_id == self.halloween_category_id and \
                    not self.get_group_by_voice_id(voice_channel_left.id):
                await voice_channel_left.delete()
