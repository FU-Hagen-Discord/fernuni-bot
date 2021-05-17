import discord

OPTIONS = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷"]


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
                if reaction not in OPTIONS[:len(self.answers)]:
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
