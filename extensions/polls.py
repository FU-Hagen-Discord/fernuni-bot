import enum
import json

import discord
import emoji
from discord import app_commands, Interaction
from discord.ext import commands

from views.poll_view import PollView

DEFAULT_CHOICES = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶",
                   "🇷", "🇸", "🇹"]


class PollType(enum.Enum):
    single_choice = "single"
    multiple_choice = "multiple"


@app_commands.guild_only()
class Polls(commands.GroupCog, name="poll", description="Handle Polls in Channels"):
    def __init__(self, bot):
        self.bot = bot
        self.polls = {}
        self.load()

    def load(self):
        try:
            with open("data/polls.json", "r") as polls_file:
                self.polls = json.load(polls_file)
        except FileNotFoundError:
            pass

    def save(self):
        with open("data/polls.json", "w") as polls_file:
            json.dump(self.polls, polls_file)

    @app_commands.command(name="add", description="Erstelle eine Umfrage mit bis zu 20 Antwortmöglichkeiten.")
    @app_commands.describe(
        type="Umfragetyp, single_choice: nur eine Antwort kann ausgewählt werden, multiple_choice: Mehrere Antwortmöglichkeiten wählbar.",
        anonymous="Bei einer Anonymen Umfrage kann nicht nachgeschaut werden, welcher Teilnehmer wofür abgestimmt hat.",
        question="Welche Frage möchtest du stellen?", choice_a="1. Antwortmöglichkeit",
        choice_b="2. Antwortmöglichkeit", choice_c="3. Antwortmöglichkeit", choice_d="4. Antwortmöglichkeit",
        choice_e="5. Antwortmöglichkeit", choice_f="6. Antwortmöglichkeit", choice_g="7. Antwortmöglichkeit",
        choice_h="8. Antwortmöglichkeit", choice_i="9. Antwortmöglichkeit", choice_j="10. Antwortmöglichkeit",
        choice_k="11. Antwortmöglichkeit", choice_l="12. Antwortmöglichkeit", choice_m="13. Antwortmöglichkeit",
        choice_n="14. Antwortmöglichkeit", choice_o="15. Antwortmöglichkeit", choice_p="16. Antwortmöglichkeit",
        choice_q="17. Antwortmöglichkeit", choice_r="18. Antwortmöglichkeit", choice_s="19. Antwortmöglichkeit",
        choice_t="20. Antwortmöglichkeit")
    async def cmd_poll(self, interaction: Interaction, type: PollType, anonymous: bool, question: str, choice_a: str,
                       choice_b: str,
                       choice_c: str = None, choice_d: str = None, choice_e: str = None, choice_f: str = None,
                       choice_g: str = None, choice_h: str = None, choice_i: str = None, choice_j: str = None,
                       choice_k: str = None, choice_l: str = None, choice_m: str = None, choice_n: str = None,
                       choice_o: str = None, choice_p: str = None, choice_q: str = None, choice_r: str = None,
                       choice_s: str = None, choice_t: str = None):
        """ Create a new poll """
        choices = [self.parse_choice(index, choice) for index, choice in enumerate(
            [choice_a, choice_b, choice_c, choice_d, choice_e, choice_f, choice_g, choice_h, choice_i, choice_j,
             choice_k, choice_l, choice_m, choice_n, choice_o, choice_p, choice_q, choice_r, choice_s, choice_t]) if
                   choice]

        await interaction.response.defer()
        poll = {"type": type.value, "anonymous": anonymous, "question": question, "author": interaction.user.id,
                "choices": choices, "participants": {}}
        await interaction.edit_original_response(embed=self.get_embed(poll), view=PollView(self))
        message = await interaction.original_response()
        self.polls[str(message.id)] = poll
        self.save()

    def get_embed(self, poll) -> discord.Embed:
        embed = discord.Embed(title="Umfrage", description=poll["question"])
        embed.add_field(name="Erstellt von", value=f'<@!{poll["author"]}>', inline=False)
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        choices = sorted(poll["choices"], key=lambda x: x[2], reverse=True)

        for choice in choices:
            name = f'{choice[0]}  {choice[1]}'
            value = f'{choice[2]}'

            embed.add_field(name=name, value=value, inline=False)

        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name="Anzahl der Teilnehmer an der Umfrage", value=f"{len(poll['participants'])}", inline=False)

        return embed

    def parse_choice(self, idx: int, choice: str):
        choice = choice.strip()
        index = choice.find(" ")

        if index > -1:
            possible_option = choice[:index]
            if emoji.is_emoji(possible_option) or possible_option in DEFAULT_CHOICES:
                if len(choice[index:].strip()) > 0:
                    return [possible_option, choice[index:].strip(), 0]
            elif len(possible_option) > 1:
                if (possible_option[0:2] == "<:" or possible_option[0:3] == "<a:") and possible_option[-1] == ">":
                    splitted_custom_emoji = possible_option.strip("<a:>").split(":")
                    if len(splitted_custom_emoji) == 2:
                        id = splitted_custom_emoji[1]
                        custom_emoji = self.bot.get_emoji(int(id))
                        if custom_emoji and len(choice[index:].strip()) > 0:
                            return [custom_emoji, choice[index:].strip(), 0]

        return [DEFAULT_CHOICES[idx], choice, 0]


async def setup(bot: commands.Bot) -> None:
    polls = Polls(bot)
    await bot.add_cog(polls)
    bot.add_view(PollView(polls))
