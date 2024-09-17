import emoji
from discord import app_commands, Interaction
from discord.ext import commands

from models import *
from views.poll_view import PollView

DEFAULT_CHOICES = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶",
                   "🇷", "🇸", "🇹"]


@app_commands.guild_only()
class Polls(commands.GroupCog, name="poll", description="Handle Polls in Channels"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add", description="Erstelle eine anonyme Umfrage mit bis zu 20 Antwortmöglichkeiten.")
    @app_commands.describe(question="Welche Frage möchtest du stellen?", choice_a="1. Antwortmöglichkeit",
                           choice_b="2. Antwortmöglichkeit", choice_c="3. Antwortmöglichkeit",
                           choice_d="4. Antwortmöglichkeit", choice_e="5. Antwortmöglichkeit",
                           choice_f="6. Antwortmöglichkeit", choice_g="7. Antwortmöglichkeit",
                           choice_h="8. Antwortmöglichkeit", choice_i="9. Antwortmöglichkeit",
                           choice_j="10. Antwortmöglichkeit", choice_k="11. Antwortmöglichkeit",
                           choice_l="12. Antwortmöglichkeit", choice_m="13. Antwortmöglichkeit",
                           choice_n="14. Antwortmöglichkeit", choice_o="15. Antwortmöglichkeit",
                           choice_p="16. Antwortmöglichkeit", choice_q="17. Antwortmöglichkeit",
                           choice_r="18. Antwortmöglichkeit", choice_s="19. Antwortmöglichkeit",
                           choice_t="20. Antwortmöglichkeit")
    async def cmd_poll(self, interaction: Interaction, question: str, choice_a: str, choice_b: str,
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

        await interaction.response.send_message("Bereite Umfrage vor, bitte warten...", view=PollView())
        message = await interaction.original_response()
        poll = Poll.create(question=question, author=interaction.user.id, channel=interaction.channel_id,
                           message=message.id)
        for choice in choices:
            PollChoice.create(poll_id=poll.id, emoji=choice[0], text=choice[1])

        await interaction.edit_original_response(content="", embed=poll.get_embed(), view=PollView())

    def parse_choice(self, idx: int, choice: str):
        choice = choice.strip()
        index = choice.find(" ")

        if index > -1:
            possible_option = choice[:index]
            if emoji.is_emoji(possible_option) or possible_option in DEFAULT_CHOICES:
                if len(choice[index:].strip()) > 0:
                    return [possible_option, choice[index:].strip()]
            elif len(possible_option) > 1:
                if (possible_option[0:2] == "<:" or possible_option[0:3] == "<a:") and possible_option[-1] == ">":
                    splitted_custom_emoji = possible_option.strip("<a:>").split(":")
                    if len(splitted_custom_emoji) == 2:
                        id = splitted_custom_emoji[1]
                        custom_emoji = self.bot.get_emoji(int(id))
                        if custom_emoji and len(choice[index:].strip()) > 0:
                            return [custom_emoji, choice[index:].strip()]

        return [DEFAULT_CHOICES[idx], choice]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
    bot.add_view(PollView())