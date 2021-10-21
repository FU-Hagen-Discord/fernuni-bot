import disnake
import emoji

DEFAULT_OPTIONS = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶",
                   "🇷"]
DELETE_POLL = "🗑️"
CLOSE_POLL = "🛑"


def is_emoji(word):
    if word in emoji.UNICODE_EMOJI_ALIAS_ENGLISH:
        return True
    elif word[:-1] in emoji.UNICODE_EMOJI_ALIAS_ENGLISH:
        return True


def get_unique_option(options):
    for option in DEFAULT_OPTIONS:
        if option not in options:
            return option


def get_options(bot, answers):
    options = []

    for i in range(min(len(answers), len(DEFAULT_OPTIONS))):
        option = ""
        answer = answers[i].strip()
        index = answer.find(" ")

        if index > -1:
            possible_option = answer[:index]
            if is_emoji(possible_option):
                if len(answer[index:].strip()) > 0:
                    option = possible_option
                    answers[i] = answer[index:].strip()
            elif len(possible_option) > 1:
                if possible_option[0:2] == "<:" and possible_option[-1] == ">":
                    splitted_custom_emoji = possible_option.strip("<:>").split(":")
                    if len(splitted_custom_emoji) == 2:
                        id = splitted_custom_emoji[1]
                        custom_emoji = bot.get_emoji(int(id))
                        if custom_emoji and len(answer[index:].strip()) > 0:
                            option = custom_emoji
                            answers[i] = answer[index:].strip()

        if (isinstance(option, str) and len(option) == 0) or option in options or option in [DELETE_POLL,
                                                                                             CLOSE_POLL]:
            option = get_unique_option(options)
        options.append(option)

    return options


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
                self.answers.append(f"{embed.fields[i].name} {embed.fields[i].value}")

        self.options = get_options(self.bot, self.answers)

    async def send_poll(self, channel, result=False, message=None):
        option_ctr = 0
        title = "Umfrage"
        participants = {}

        if result:
            title += " Ergebnis"

        if len(self.answers) > len(DEFAULT_OPTIONS):
            await channel.send(
                f"Fehler beim Erstellen der Umfrage! Es werden nicht mehr als {len(DEFAULT_OPTIONS)} Optionen unterstützt!")
            return

        embed = disnake.Embed(title=title, description=self.question)
        embed.add_field(name="Erstellt von", value=f'<@!{self.author}>', inline=False)
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        for i in range(0, len(self.answers)):
            name = f'{self.options[i]}'
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
                if reaction not in self.options:
                    await message.clear_reaction(reaction)

            for i in range(0, len(self.answers)):
                if self.options[i] not in reactions:
                    await message.add_reaction(self.options[i])

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
