import os

import discord
from discord.ext import commands

import utils

OPTIONS = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷"]


class PollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.poll_sugg_channel = int(os.getenv("DISCORD_POLL_SUGG_CHANNEL"))

    @commands.command(name="add-poll")
    async def cmd_add_poll(self, ctx, question, *answers):
        channel = await self.bot.fetch_channel(self.poll_sugg_channel)
        msg = f"<@!{ctx.author.id}> hat folgende Umfrage vorgeschlagen:\nFrage:{question}\n\nAntwortoptionen:\n"

        for answer in answers:
            msg += f"{answer}"

        await channel.send(msg)

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
                    # value += f'\nStimmen: '

                    # async for user in reaction.users():
                    #     if self.bot.user == user:
                    #         continue
                    #     ping = f'<@!{str(user.id)}> '
                    #
                    #     if len(value) + len(ping) > 1024:
                    #         embed.add_field(name=name, value=value, inline=False)
                    #         answer = f''
                    #         name = "\u200b"
                    #     elif
                    #
                    #     value += ping

            embed.add_field(name=name, value=value, inline=False)
            option_ctr += 1

        if message:
            await message.edit(embed=embed)
        else:
            message = await channel.send("", embed=embed)

        await message.clear_reaction("🗑️")
        await message.clear_reaction("🛑")

        if not result:
            for i in range(0, len(self.answers)):
                await message.add_reaction(OPTIONS[i])

            for i in range(len(self.answers), len(OPTIONS)):
                await message.clear_reaction(OPTIONS[i])

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
