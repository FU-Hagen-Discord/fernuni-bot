import json
import os
from asyncio import sleep
import random
from datetime import datetime, timedelta
from copy import deepcopy

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
        poll = {'question': question,
                'answers': [[answer, 0] for answer in answers],
                'voter': []}

        msg = await ctx.send(embed=self.create_poll_embed(poll), components=self.create_components(poll))

        # Speichere Frage und zugehörige Antworten mit Anzahl ihrer bisherigen Votes (0 in diesem Fall)
        self.active_polls[str(msg.id)] = poll
        self.save_polls()

    def create_poll_embed(self, poll):
        embed = discord.Embed(title=f"Umfrage: {poll['question']}",
                              description="\n".join([f"`[{answer[1]}]` {answer[0]}" for answer in poll['answers']]),
                              color=discord.Colour.green())
        return embed

    def create_components(self, poll):
        button_row = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="Umfrage beenden",
                custom_id="quit"
            ))

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
        # change_vote_nums
        # change_poll_message

        labels = [option.label for option in inter.select_menu.selected_options]
        values = [option.value for option in inter.select_menu.selected_options]

        if poll := self.active_polls.get(str(inter.message.id)):
            for value in values:
                poll['answers'][int(value)][1] += 1
        self.save_polls()
        await inter.reply(embed=self.create_poll_embed(poll), components=self.create_components(poll), type=7)

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        clicked_button = inter.clicked_button.custom_id
        if clicked_button == "quit":
            await inter.reply(type=7)

    #@cmd_pollselect.error
    #async def pollselect_error(self, ctx, error):
    #    await ctx.send("Das habe ich nicht verstanden. Die Pollselect-Syntax ist:\n"
    #                   "`!pollselect <question> <answers...>`\n")