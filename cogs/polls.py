import os

from discord.ext import commands

import utils
from cogs.components.poll.poll import Poll
from cogs.help import help, handle_error, help_category


@help_category("poll", "Umfragen", "Erstelle eine Umfrage in einem Kanal oder schlage eine Server-Umfrage vor.",
               "Umfragen erstellen oder bearbeiten.")
class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.poll_sugg_channel = int(os.getenv("DISCORD_POLL_SUGG_CHANNEL"))

    @help(
        category="poll",
        syntax="!add-poll <question> <answers...>",
        brief="Schlägt eine Umfrage für den Umfrage-Kanal vor.",
        parameters={
            "question": "Die Frage die gestellt werden soll (in Anführungszeichen).",
            "answers...": "Durch Leerzeichen getrennte Antwortmöglichkeiten (die einzelnen Antworten in Anführungszeichen einschließen)."
        },
        example="!add-poll \"Wie ist das Wetter?\" \"echt gut\" \"weniger gut\" \"Boar nee, nicht schon wieder Regen\""
    )
    @commands.command(name="add-poll")
    async def cmd_add_poll(self, ctx, question, *answers):
        channel = await self.bot.fetch_channel(self.poll_sugg_channel)
        msg = f"<@!{ctx.author.id}> hat folgende Umfrage vorgeschlagen:\nFrage:{question}\n\nAntwortoptionen:\n"
        poll = f"!poll \"{question}\""

        for answer in answers:
            msg += f"{answer}\n"
            poll += f" \"{answer}\""

        await channel.send(f"{msg}\n{poll}")

    @help(
        category="poll",
        brief="Bearbeitet eine bereits vorhandene Umfrage.",
        syntax="!edit-poll <message_id> <question> <answers...>",
        parameters={
            "message_id": "die Message-ID ist der Nachricht mit einem Rechtsklick auf die Umfrage zu entnehmen (Entwicklermodus in Discord müssen aktiv sein).",
            "question": "Die Frage, die gestellt werden soll (in Anführungszeichen).",
            "answers...": "Durch Leerzeichen getrennte Antwortmöglichkeiten (die einzelnen Antworten in Anführungszeichen einschließen).",
        },
        example="!edit-poll 838752355595059230 \"Wie ist das Wetter?\" \"echt gut\" \"weniger gut\" \"Boar nee, nicht schon wieder Regen\"",
        mod=True
    )
    @commands.command(name="edit-poll")
    @commands.check(utils.is_mod)
    async def cmd_edit_poll(self, ctx, message_id, question, *answers):
        message = await ctx.fetch_message(message_id)
        if message:
            if message.embeds[0].title == "Umfrage":
                old_poll = Poll(self.bot, message=message)
                new_poll = Poll(self.bot, question=question, answers=answers, author=old_poll.author)
                await new_poll.send_poll(ctx.channel, message=message)
        else:
            ctx.send("Fehler! Umfrage nicht gefunden!")
        pass

    @help(
        category="poll",
        syntax="!poll <question> <answers...>",
        brief="Erstellt eine Umfrage im aktuellen Kanal.",
        parameters={
            "question": "Die Frage, die gestellt werden soll (in Anführungszeichen).",
            "answers...": "Durch Leerzeichen getrennte Antwortmöglichkeiten (die einzelnen Antworten in Anführungszeichen einschließen)."
        },
        example="!poll \"Wie ist das Wetter?\" \"echt gut\" \"weniger gut\" \"Boar nee, nicht schon wieder Regen\""
    )
    @commands.command(name="poll")
    async def cmd_poll(self, ctx, question, *answers):
        """ Create poll """

        await Poll(self.bot, question, answers, ctx.author.id).send_poll(ctx)

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

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
