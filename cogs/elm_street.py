import json
import os
from typing import Union

import disnake
from disnake import ApplicationCommandInteraction, ButtonStyle
from disnake.ext import commands
from dotenv import load_dotenv

load_dotenv()


def get_player_from_embed(embed: disnake.Embed):
    return embed.description.split()[0][2:-1]


class ElmStreet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.groups = {}
        self.players = {}
        self.load()
        self.elm_street_channel_id = int(os.getenv("DISCORD_ELM_STREET_CHANNEL"))
        self.bot.view_manager.register("on_join", self.on_join)
        self.bot.view_manager.register("on_joined", self.on_joined)
        self.bot.view_manager.register("on_start", self.on_start)

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

        if not self.is_playing(author.id):
            thread = await channel.create_thread(name=name, auto_archive_duration=1440, type=channel_type)

            await thread.send(f"Hallo {author.mention}. Der Streifzug deiner Gruppe durch die Elm-Street findet "
                              f"in diesem Thread statt. Sobald deine Gruppe sich zusammen  gefunden hat, kannst "
                              f"du über einen Klick auf den Start Button eure Reise starten.",
                              view=self.get_start_view())

            await interaction.response.send_message(
                f"Du bist mitten in einer Großstadt gelandet.\n"
                f"Der leise Wind weht Papier die Straße lang.\n"
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
                f"Du drehst dich zur Tür und siehst {author.mention}",
                view=self.get_join_view(thread.id))

            message = await interaction.original_message()
            self.groups[str(thread.id)] = {"message": message.id, "players": [author.id], "owner": author.id}
            self.save()
        else:
            await interaction.response.send_message(
                "Es tut mir leid, aber du kannst nicht an mehr als einer Jagd gleichzeitig teilnehmen. "
                "Beende erst das bisherige Abenteuer, bevor du dich einer neuen Gruppe anschließen kannst.",
                ephemeral=True)

    async def on_join(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        player = self.get_player(interaction.author)

        try:
            if group := self.groups.get(str(value)):
                if not self.is_already_in_this_group(interaction.author.id, interaction.message.id):
                    if not self.is_playing(interaction.author.id):
                        thread = await self.bot.fetch_channel(value)
                        await self.bot.view_manager.confirm(thread, "Neuer Rekrut",
                                      f"{interaction.author.mention} würde sich gerne der Gruppe anschließen",
                                      custom_prefix="rekrut",
                                      callback_key="on_joined")
                    else:
                        await interaction.response.send_message(
                            "Es tut mir leid, aber du kannst nicht an mehr als einer Jagd gleichzeitig teilnehmen. "
                            "Beende erst das bisherige Abenteuer, bevor du dich einer neuen Gruppe anschließen kannst.",
                            ephemeral=True)
                else:
                    await interaction.response.send_message("Du bist schon Teil dieser Gruppe! Schau doch mal in eurem "
                                                            "Thread vorbei.", ephemeral=True)
        except:
            await interaction.response.send_message(
                "Ein Fehler ist aufgetreten. Überprüfe bitte, ob du der richtigen Gruppe beitreten wolltest. "
                "Sollte der Fehler erneut auftreten, wende dich bitte an einen Mod.",
                ephemeral=True)

        if not interaction.response.is_done():
            await interaction.response.send_message("Dein Wunsch, der Gruppe beizutreten wurde weitergeleitet.",
                                                    ephemeral=True)

    async def on_joined(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        player_id = int(get_player_from_embed(interaction.message.embeds[0]))
        thread_id = interaction.channel_id
        owner_id = self.groups.get(str(thread_id)).get('owner')

        if interaction.author.id == owner_id:
            if value:
                if group := self.groups.get(str(interaction.channel_id)):
                    if not self.is_playing(player_id):
                        group["players"].append(player_id)
                        await interaction.message.channel.send(
                            f"<@!{player_id}> ist jetzt Teil der Crew! Herzlich willkommen.")
                        self.save()
            else:
                user = self.bot.get_user(player_id)
                groupname = interaction.channel.name
                await send_dm(user, f"Die Gruppe {groupname} hat entschieden, dich nicht mitlaufen zu lassen, du siehst"
                                    f" nicht gruselig genug aus. Zieh dich um und versuch es noch einmal.")
            await interaction.message.delete()
        else:
            await interaction.response.send_message("Nur die Gruppenerstellerin kann User annehmen oder ablehnen.",
                                                    ephemeral=True)

    async def on_start(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        thread_id = interaction.channel_id
        owner_id = self.groups.get(str(thread_id)).get('owner')
        if interaction.author.id == owner_id:
            if group := self.groups.get(str(interaction.channel.id)):
                await interaction.response.send_message("Leute, der Spaß beginnt.... j@@@@@@@@@")
                elm_street_channel = await self.bot.fetch_channel(self.elm_street_channel_id)
                group_message = await elm_street_channel.fetch_message(group["message"])
                await group_message.delete()
                await interaction.message.edit(view=self.get_start_view(disabled=True))
        else:
            await interaction.response.send_message("Nur die Gruppenerstellerin kann die Gruppe starten lassen.",
                                                    ephemeral=True)

    def get_join_view(self, group_id: int):
        buttons = [
            {"label": "Join", "style": ButtonStyle.green, "value": group_id, "custom_id": "elm_street:join"}
        ]
        return self.bot.view_manager.view(buttons, "on_join")

    def get_start_view(self, disabled=False):
        buttons = [
            {"label": "Start", "style": ButtonStyle.green, "custom_id": "elm_street:start", "disabled": disabled}
        ]
        return self.bot.view_manager.view(buttons, "on_start")

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
