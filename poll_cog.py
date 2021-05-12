import os

import discord
from discord.ext import commands

import utils
from help.help import help, handle_error, help_category

OPTIONS = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷"]

@help_category("poll", "Umfragen", "Erstelle eine Umfrage in einem Kanal oder schlage eine Server-Umfrage vor.", "Umfragen erstellen oder bearbeiten.")
class PollCog(commands.Cog):
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
        poll = f"!poll \"{queestion}\""
        
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


class Poll:

    def __init__(self, bot, question=None, answers=None, author=None, message=None):
        self.bot = bot
        self.question = question
        self.answers = answers
        self.author = author

        if message:
            self.message = message
            self.answers = []
            embed = message.embeds[0]
            self.author = embed.fields[0].value[3:-1]
            self.question = embed.description
            for i in range(2, len(embed.fields)):
                self.answers.append(embed.fields[i].value)

    async def send_poll(self, channel, result=False, message=None):
        option_ctr = 0
        title = "Umfrage"
        participants = {}

        if result:
            title += " Ergebnis"

        if len(self.answers) > len(OPTIONS):
            await channel.send(
                f"Fehler beim Erstellen der Umfrage! Es werden nicht mehr als {len(OPTIONS)} Optionen unterstützt!")
            return

        embed = discord.Embed(title=title, description=self.question)
        embed.add_field(name="Erstellt von", value=f'<@!{self.author}>', inline=False)
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        for i in range(0, len(self.answers)):
            name = f'{OPTIONS[i]}'
            value = f'{self.answers[i]}'

            if result:
                reaction = self.get_reaction(name)
                if reaction:
                    name += f' : {reaction.count - 1}'
                    async for user in reaction.users():
                        if user != self.bot.user:
                            participants[str(user.id)] = 1

            embed.add_field(name=name, value=value, inline=False)
            option_ctr += 1

        if result:
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            embed.add_field(name="Anzahl Teilnehmer an der Umfrage", value=f"{len(participants)}", inline=False)

        if message:
            await message.edit(embed=embed)
        else:
            message = await channel.send("", embed=embed)

        reactions = []
        for reaction in message.reactions:
            reactions.append(reaction.emoji)

        if not result:
            await message.clear_reaction("🗑️")
            await message.clear_reaction("🛑")

            for reaction in reactions:
                if reaction not in OPTIONS[:len(self.answers) - 1]:
                    await message.clear_reaction(reaction)

            for i in range(0, len(self.answers)):
                if OPTIONS[i] not in reactions:
                    await message.add_reaction(OPTIONS[i])

            await message.add_reaction("🗑️")
            await message.add_reaction("🛑")

    async def close_poll(self):
        await self.send_poll(self.message.channel, result=True)
        await self.delete_poll()

    async def delete_poll(self):
        await self.message.delete()

    def get_reaction(self, reaction):
        if self.message:
            reactions = self.message.reactions

            for react in reactions:
                if react.emoji == reaction:
                    return react
