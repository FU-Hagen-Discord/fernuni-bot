import json
import os

import discord
from discord.ext import commands, tasks
from dislash import *

from cogs.help import help


class Pollselect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}
        self.polls_path = os.getenv("DISCORD_POLLSELECT_FILE")
        self.load_polls()

    def load_polls(self):
        polls_file = open(self.polls_path, mode='r')
        self.active_polls = json.load(polls_file)

    def save_polls(self):
        polls_file = open(self.polls_path, mode='w')
        json.dump(self.active_polls, polls_file)

    @commands.command(name="pollselect")
    async def cmd_pollselect(self, ctx, question, *answers):
        poll = {'author_id': str(ctx.author.id),
                'author_mention': ctx.author.mention,
                'question': question,
                'answers': [[answer, 0] for answer in answers],
                'voter': {}}
        msg = await ctx.send(embed=self.create_poll_embed(poll), components=self.create_components(poll))

        # Speichere Frage und zugehörige Antworten mit Anzahl ihrer bisherigen Votes (0 in diesem Fall)
        self.active_polls[str(msg.id)] = poll
        self.save_polls()

    def create_poll_embed(self, poll):
        embed = discord.Embed(title=f"Umfrage: {poll['question']}",
                              description=f"erstellt von {poll['author_mention']}",
                              color=discord.Colour.green())
        embed.add_field(name='[Votes] Antwortmöglichkeiten:',
                        value="\n".join([f"`[{answer[1]}]` {answer[0]}" for answer in poll['answers']]))
        return embed

    def create_components(self, poll):
        button_row = ActionRow(
            Button(
                style=ButtonStyle.grey,
                emoji="🛑",
                custom_id="quit"
            ),
            Button(
                style=ButtonStyle.grey,
                emoji="🗑️",
                custom_id="delete"
            )
        )

        answer_num = len(poll['answers'])
        options = []
        for i in range(answer_num):
            options.append(SelectOption(poll['answers'][i][0], str(i)))

        select_menu = SelectMenu(
            custom_id="poll",
            placeholder="Wähle deine Antworten",
            max_values=answer_num,
            options=options
        )
        return [select_menu, button_row]

    @commands.Cog.listener()
    async def on_dropdown(self, inter):
        # Addiert die Auswahl des Users zum Ergebnis der einzelnen Antworten
        # wenn der User schon gevotet hat, wird nur die neue Auswahl gezählt
        # zum Sicherstellen, dass nur einmal abgestimmt werden kann, wird die Auswahl
        # des Users zusammen mit seiner ID gespeichert

        values = [option.value for option in inter.select_menu.selected_options]
        if poll := self.active_polls.get(str(inter.message.id)):
            for value in values:
                poll['answers'][int(value)][1] += 1
        if voter := poll['voter'].get(str(inter.author.id)):
            for value in voter:
                poll['answers'][int(value)][1] -= 1
        poll['voter'][str(inter.author.id)] = values
        self.save_polls()
        await inter.reply(embed=self.create_poll_embed(poll), components=self.create_components(poll), type=7)

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        clicked_button = inter.clicked_button.custom_id
        if clicked_button == "quit":
            await self.quit_poll(inter)
        if clicked_button == "delete":
            await self.delete_poll(inter)

    async def quit_poll(self, inter):
        if poll := self.active_polls.get(str(inter.message.id)):
            if str(inter.author.id) == poll['author_id']:
                # Antworten in absteigender Reihenfolge (Anzahl der Votes) ausgeben
                answers = sorted(poll['answers'], key=lambda x: x[1], reverse=True)
                embed = discord.Embed(title=f"Ergebnis: {poll['question']}",
                                      description=f"erstellt von {poll['author_mention']}",
                                      color=discord.Colour.red())
                embed.add_field(name='Anzahl der Votes:',
                                value="\n".join([f"`[{answer[1]}]` {answer[0]}" for answer in answers]),
                                inline=False)
                embed.add_field(name='Anzahl der Voter_innen:',
                                value=str(len(poll['voter'])),
                                inline=False)
                await inter.channel.send(embed=embed)
                await inter.message.delete()
                self.active_polls.pop(str(inter.message.id))
                self.save_polls()
            else:
                await inter.reply("Nur die Poll-Erstellerin selbst darf ihn auch beenden.", ephemeral=True)

    async def delete_poll(self, inter):
        if poll := self.active_polls.get(str(inter.message.id)):
            if str(inter.author.id) == poll['author_id']:
                await inter.message.delete()
                self.active_polls.pop(str(inter.message.id))
                self.save_polls()
            else:
                await inter.reply("Nur die Poll-Erstellerin selbst darf ihn auch beenden.", ephemeral=True)

    @cmd_pollselect.error
    async def pollselect_error(self, ctx, error):
        await ctx.send("Das habe ich nicht verstanden. Die Pollselect-Syntax ist:\n"
                       "`!pollselect <question> <answers...>`\n")