import os

from discord import Interaction, app_commands
from discord.ext import commands

from extensions.components.poll.poll import Poll


class Polls(commands.GroupCog, name="poll", description="Handle Polls in Channels"):
    def __init__(self, bot):
        self.bot = bot
        self.poll_sugg_channel = int(os.getenv("DISCORD_POLL_SUGG_CHANNEL"))

    @app_commands.command(name="add", description="Erstelle eine Umfrage mit bis zu 20 Antwortmöglichkeiten.")
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
        await interaction.response.defer()
        """ Create poll """
        answers = [choice for choice in
                   [choice_a, choice_b, choice_c, choice_d, choice_e, choice_f, choice_g, choice_h, choice_i, choice_j,
                    choice_k, choice_l, choice_m, choice_n, choice_o, choice_p, choice_q, choice_r, choice_s, choice_t]
                   if choice]

        await Poll(self.bot, question, list(answers), interaction.user.id).send_poll(interaction)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.emoji.name in ["🗑️", "🛑"]:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds) > 0 and message.embeds[0].title == "Umfrage":
                poll = Poll(self.bot, message=message)
                if str(payload.user_id) == poll.author:
                    if payload.emoji.name == "🗑️":
                        await poll.delete_poll()
                    else:
                        await poll.close_poll()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
