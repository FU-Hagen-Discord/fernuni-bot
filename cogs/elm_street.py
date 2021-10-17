import json
import os
from typing import Union

import disnake
from disnake import ApplicationCommandInteraction, \
    ButtonStyle
from disnake.ext import commands
from dotenv import load_dotenv

from views import dialog_view

load_dotenv()


class ElmStreet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.groups = {}
        self.players = {}
        self.load()
        self.elm_street_channel_id = int(os.getenv("DISCORD_ELM_STREET_CHANNEL"))

    def load(self):
        with open("data/elm_street_groups.json", "r") as groups_file:
            self.groups = json.load(groups_file)
        with open("data/elm_street_players.json", "r") as players_file:
            self.players = json.load(players_file)

    def save(self):
        with open("data/elm_street_groups.json", "w") as groups_file:
            json.dump(self.groups, groups_file)
        with open("data/elm_street_players.json", "w") as players_file:
            json.dump(self.players, players_file)

    @commands.slash_command(name="start-group",
                            description="Erstelle eine Gruppe für einen Streifzug durch die Elm Street",
                            guild_ids=[int(os.getenv('DISCORD_GUILD'))])
    async def cmd_start_group(self, interaction: ApplicationCommandInteraction, name: str):
        author = interaction.author
        channel = await self.bot.fetch_channel(self.elm_street_channel_id)
        channel_type = None if self.bot.is_prod() else disnake.ChannelType.public_thread
        player = self.get_player(author)

        if not self.is_playing(author):
            thread = await channel.create_thread(name=name, auto_archive_duration=1440, type=channel_type)
            self.groups[str(thread.id)] = {"players": [author.id]}
            self.save()

            await thread.send(f"Hallo {author.mention}. Der Streifzug deiner Gruppe durch die Elm-Street findet "
                              f"in diesem Thread statt. Du kannst über das Command! Sobald deine Gruppe sich zusammen"
                              f"gefunden hat, kannst du über einen Klick auf den Start Button eure Reise starten.",
                              view=self.get_start_view())

            await interaction.response.send_message(f":rotating_light:{author.mention} stellt gerade die Gruppe {name} "
                                                    f"für einen Streifzug durch die Elm Street. Verwende "
                                                    f"`/join-group {thread.id}`, um dich der Jagd anzuschließen!",
                                                    view=self.get_join_view(thread.id))
        else:
            await interaction.response.send_message(
                "Es tut mir leid, aber du kannst nicht an mehr als einer Jagd gleichzeitig teilnehmen. "
                "Beende erst das bisherige Abenteuer, bevor du dich einer neuen Gruppe anschließen kannst.",
                ephemeral=True)

    async def on_join(self, button: disnake.ui.Button, interaction: disnake.InteractionMessage, value=None):
        player = self.get_player(interaction.author)

        try:
            if group := self.groups.get(str(value)):
                if not self.is_playing(interaction.author):
                    thread = await self.bot.fetch_channel(value)
                    group["players"].append(interaction.author.id)

                    self.save()

                else:
                    await interaction.response.send_message(
                        "Es tut mir leid, aber du kannst nicht an mehr als einer Jagd gleichzeitig teilnehmen. "
                        "Beende erst das bisherige Abenteuer, bevor du dich einer neuen Gruppe anschließen kannst.",
                        ephemeral=True)
        except:
            await interaction.response.send_message(
                "Ein Fehler ist aufgetreten. Überprüfe bitte, ob du der richtigen Gruppe beitreten wolltest. "
                "Sollte der Fehler erneut auftreten, wende dich bitte an einen Mod.",
                ephemeral=True)

        if not interaction.response.is_done():
            await interaction.response.send_message("Du bist der Gruppe beigetreten =) GEIL GEIL GEIL", ephemeral=True)

    async def on_start(self, button: disnake.ui.Button, interaction: disnake.InteractionMessage, value=None):
        await interaction.response.send_message("Leute, der Spaß beginnt.... j@@@@@@@@@")

    def get_join_view(self, group_id: int):
        buttons = [
            {"label": "Join", "style": ButtonStyle.green, "value": group_id, "custom_id": "elm_street:join"}
        ]
        return dialog_view.DialogView(buttons, self.on_join)

    def get_start_view(self):
        buttons = [
            {"label": "Start", "style": ButtonStyle.green, "custom_id": "elm_street:start"}
        ]
        return dialog_view.DialogView(buttons, self.on_start)

    def is_playing(self, user: Union[disnake.User, disnake.Member]):
        for group in self.groups.values():
            if players := group.get("players"):
                if user.id in players:
                    return True

        return False

    def can_play(self, user: Union[disnake.User, disnake.Member]):
        # TODO Check whether Player is ready to play.
        return True

    def get_player(self, user: Union[disnake.User, disnake.Member]):
        if player := self.players.get(str(user.id)):
            return player
        else:
            player = {"courage": 100, "sweets": 0}
            self.players[str(user.id)] = player
            self.save()
            return player
